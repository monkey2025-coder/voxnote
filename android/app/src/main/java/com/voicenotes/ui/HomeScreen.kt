package com.voicenotes.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Mic
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.Card
import androidx.compose.material3.ExtendedFloatingActionButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalLifecycleOwner
import androidx.compose.ui.unit.dp
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import com.voicenotes.data.model.Project
import com.voicenotes.data.network.ApiClient
import com.voicenotes.data.repository.PendingUploads
import com.voicenotes.data.repository.TokenStore
import kotlinx.coroutines.flow.firstOrNull
import kotlinx.coroutines.launch

@Composable
fun HomeScreen(onRecord: () -> Unit, onSettings: () -> Unit, onLogout: () -> Unit) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    var projects by remember { mutableStateOf<List<Project>>(emptyList()) }
    var inboxCount by remember { mutableIntStateOf(0) }
    var pendingCount by remember { mutableIntStateOf(0) }
    var username by remember { mutableStateOf("") }
    var message by remember { mutableStateOf<String?>(null) }

    suspend fun refresh() {
        try {
            projects = ApiClient.projects.list()
            inboxCount = ApiClient.projects.inbox().size
            message = null
        } catch (e: Exception) {
            message = "加载失败,请检查服务器连接"
        }
        username = TokenStore.usernameFlow(context).firstOrNull() ?: ""
        pendingCount = PendingUploads.list(context).size
    }

    // 每次回到首页(首次进入/从设置或录音页返回):补传离线队列 + 拉取数据
    val lifecycleOwner = LocalLifecycleOwner.current
    DisposableEffect(lifecycleOwner) {
        val observer = LifecycleEventObserver { _, event ->
            if (event == Lifecycle.Event.ON_RESUME) {
                scope.launch {
                    PendingUploads.retryAll(context)
                    refresh()
                }
            }
        }
        lifecycleOwner.lifecycle.addObserver(observer)
        onDispose { lifecycleOwner.lifecycle.removeObserver(observer) }
    }

    Scaffold(
        floatingActionButton = {
            ExtendedFloatingActionButton(
                onClick = onRecord,
                icon = { Icon(Icons.Default.Mic, contentDescription = null) },
                text = { Text("开始录音") },
            )
        },
    ) { padding ->
        Column(
            Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(horizontal = 16.dp)
        ) {
            Spacer(Modifier.height(16.dp))
            Row(
                Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text("你好,$username", Modifier.weight(1f), style = MaterialTheme.typography.titleLarge)
                IconButton(onClick = onSettings) {
                    Icon(Icons.Default.Settings, contentDescription = "服务器设置")
                }
                TextButton(onClick = {
                    scope.launch {
                        TokenStore.clear(context)
                        ApiClient.configure(newToken = null)
                        onLogout()
                    }
                }) { Text("退出登录") }
            }

            if (pendingCount > 0) {
                Card(Modifier.fillMaxWidth().padding(vertical = 8.dp)) {
                    Row(
                        Modifier.padding(12.dp),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Text("$pendingCount 条语音待上传", Modifier.weight(1f))
                        TextButton(onClick = {
                            scope.launch {
                                pendingCount = PendingUploads.retryAll(context)
                                refresh()
                            }
                        }) { Text("重试上传") }
                    }
                }
            }

            if (message != null) {
                Text(message!!, color = MaterialTheme.colorScheme.error)
            }

            Spacer(Modifier.height(8.dp))
            Text("未整理语音:$inboxCount 条(请在网页端整理到项目)", style = MaterialTheme.typography.bodyMedium)
            Spacer(Modifier.height(16.dp))

            Text("我的项目", style = MaterialTheme.typography.titleMedium)
            Spacer(Modifier.height(8.dp))
            if (projects.isEmpty()) {
                Box(Modifier.fillMaxWidth().padding(24.dp), contentAlignment = Alignment.Center) {
                    Text("暂无项目,可在网页端创建", color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            } else {
                LazyColumn {
                    items(projects) { p ->
                        Card(Modifier.fillMaxWidth().padding(vertical = 4.dp)) {
                            Row(
                                Modifier.padding(16.dp),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.CenterVertically,
                            ) {
                                Text(p.name, style = MaterialTheme.typography.titleSmall)
                                Text("${p.note_count} 条", color = MaterialTheme.colorScheme.onSurfaceVariant)
                            }
                        }
                    }
                }
            }
        }
    }
}
