package com.voicenotes.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Settings
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import com.voicenotes.data.network.ApiClient
import com.voicenotes.data.repository.TokenStore
import kotlinx.coroutines.launch

@Composable
fun LoginScreen(onSuccess: () -> Unit, onSettings: () -> Unit) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    var username by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    var isRegister by remember { mutableStateOf(false) }
    var loading by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(24.dp),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Box(Modifier.fillMaxWidth()) {
            IconButton(onClick = onSettings, modifier = Modifier.align(Alignment.TopEnd)) {
                Icon(Icons.Default.Settings, contentDescription = "服务器设置")
            }
        }
        Text("语音记事本", style = MaterialTheme.typography.headlineMedium)
        Spacer(Modifier.height(24.dp))
        OutlinedTextField(
            value = username,
            onValueChange = { username = it },
            label = { Text("用户名") },
            singleLine = true,
            modifier = Modifier.fillMaxWidth(),
        )
        Spacer(Modifier.height(12.dp))
        OutlinedTextField(
            value = password,
            onValueChange = { password = it },
            label = { Text("密码") },
            visualTransformation = PasswordVisualTransformation(),
            singleLine = true,
            modifier = Modifier.fillMaxWidth(),
        )
        if (error != null) {
            Spacer(Modifier.height(8.dp))
            Text(error!!, color = MaterialTheme.colorScheme.error)
        }
        Spacer(Modifier.height(20.dp))
        Button(
            onClick = {
                scope.launch {
                    loading = true
                    error = null
                    try {
                        val body = mapOf("username" to username.trim(), "password" to password)
                        val resp = if (isRegister) ApiClient.auth.register(body) else ApiClient.auth.login(body)
                        ApiClient.configure(newToken = resp.access_token)
                        TokenStore.save(context, resp.access_token, username.trim())
                        onSuccess()
                    } catch (e: Exception) {
                        error = if (isRegister) "注册失败,用户名可能已被占用" else "登录失败,请检查用户名和密码"
                    } finally {
                        loading = false
                    }
                }
            },
            enabled = !loading && username.isNotBlank() && password.isNotBlank(),
            modifier = Modifier.fillMaxWidth(),
        ) {
            Text(if (loading) "请稍候…" else if (isRegister) "注册" else "登录")
        }
        TextButton(onClick = { isRegister = !isRegister; error = null }) {
            Text(if (isRegister) "已有账号?去登录" else "没有账号?去注册")
        }
    }
}
