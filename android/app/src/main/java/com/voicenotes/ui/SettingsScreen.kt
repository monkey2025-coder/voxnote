package com.voicenotes.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.Button
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import com.voicenotes.data.network.ApiClient
import com.voicenotes.data.repository.TokenStore
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch

private fun isValidUrl(url: String): Boolean {
    val u = url.trim().trimEnd('/')
    return (u.startsWith("http://") || u.startsWith("https://")) &&
        u.length > "http://x".length
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(onBack: () -> Unit) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    var url by remember { mutableStateOf("") }
    var loaded by remember { mutableStateOf(false) }
    var testing by remember { mutableStateOf(false) }
    var saving by remember { mutableStateOf(false) }
    var message by remember { mutableStateOf<String?>(null) }
    var messageOk by remember { mutableStateOf(false) }

    LaunchedEffect(Unit) {
        url = TokenStore.serverFlow(context).first()
        loaded = true
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("服务器设置") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "返回")
                    }
                },
            )
        },
    ) { padding ->
        Column(
            Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(24.dp)
        ) {
            Text("服务器地址", style = MaterialTheme.typography.titleMedium)
            Spacer(Modifier.height(8.dp))
            OutlinedTextField(
                value = url,
                onValueChange = { url = it; message = null },
                label = { Text("例如 http://192.168.1.10:8000") },
                singleLine = true,
                enabled = loaded,
                modifier = Modifier.fillMaxWidth(),
            )
            Spacer(Modifier.height(8.dp))
            Text(
                "模拟器用 http://10.0.2.2:8000;真机请填电脑的局域网 IP 或公网域名,手机需与服务器网络互通。",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )

            if (message != null) {
                Spacer(Modifier.height(8.dp))
                Text(
                    message!!,
                    color = if (messageOk) MaterialTheme.colorScheme.primary
                    else MaterialTheme.colorScheme.error,
                )
            }

            Spacer(Modifier.height(20.dp))
            Row(
                Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                OutlinedButton(
                    onClick = {
                        scope.launch {
                            val target = url.trim().trimEnd('/')
                            if (!isValidUrl(target)) {
                                messageOk = false
                                message = "地址格式不正确,需以 http:// 或 https:// 开头"
                                return@launch
                            }
                            testing = true
                            message = null
                            ApiClient.configure(newBaseUrl = target)
                            val ok = runCatching { ApiClient.health.ping() }.isSuccess
                            testing = false
                            if (ok) {
                                messageOk = true
                                message = "连接成功"
                            } else {
                                messageOk = false
                                message = "无法连接到该地址,请检查网络和端口"
                            }
                        }
                    },
                    enabled = !testing && !saving && loaded,
                    modifier = Modifier.weight(1f),
                ) { Text(if (testing) "测试中…" else "测试连接") }

                Button(
                    onClick = {
                        scope.launch {
                            val target = url.trim().trimEnd('/')
                            if (!isValidUrl(target)) {
                                messageOk = false
                                message = "地址格式不正确,需以 http:// 或 https:// 开头"
                                return@launch
                            }
                            saving = true
                            TokenStore.saveServer(context, target)
                            ApiClient.configure(newBaseUrl = target)
                            saving = false
                            onBack()
                        }
                    },
                    enabled = !testing && !saving && loaded,
                    modifier = Modifier.weight(1f),
                ) { Text(if (saving) "保存中…" else "保存") }
            }

            Spacer(Modifier.height(24.dp))
            Text(
                "提示:更换服务器后,登录账号也需要是该服务器上注册的账号。",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}
