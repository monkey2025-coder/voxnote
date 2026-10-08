package com.voicenotes.ui

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.voicenotes.data.network.ApiClient
import com.voicenotes.data.repository.TokenStore
import kotlinx.coroutines.flow.firstOrNull

object Routes {
    const val LOGIN = "login"
    const val HOME = "home"
    const val RECORD = "record"
    const val SETTINGS = "settings"
}

@Composable
fun AppNavHost() {
    val nav = rememberNavController()
    val context = LocalContext.current
    var start by remember { mutableStateOf<String?>(null) }

    // 读取服务器地址和登录状态
    LaunchedEffect(Unit) {
        val server = TokenStore.serverFlow(context).firstOrNull() ?: ApiClient.DEFAULT_URL
        val token = TokenStore.tokenFlow(context).firstOrNull()
        ApiClient.configure(newBaseUrl = server, newToken = token)
        start = if (!token.isNullOrEmpty()) Routes.HOME else Routes.LOGIN
    }

    val startDest = start
    if (startDest == null) {
        Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            CircularProgressIndicator()
        }
        return
    }

    NavHost(navController = nav, startDestination = startDest) {
        composable(Routes.LOGIN) {
            LoginScreen(
                onSuccess = {
                    nav.navigate(Routes.HOME) { popUpTo(Routes.LOGIN) { inclusive = true } }
                },
                onSettings = { nav.navigate(Routes.SETTINGS) },
            )
        }
        composable(Routes.HOME) {
            HomeScreen(
                onRecord = { nav.navigate(Routes.RECORD) },
                onSettings = { nav.navigate(Routes.SETTINGS) },
                onLogout = {
                    nav.navigate(Routes.LOGIN) { popUpTo(Routes.HOME) { inclusive = true } }
                },
            )
        }
        composable(Routes.RECORD) {
            RecordScreen(onDone = { nav.popBackStack() })
        }
        composable(Routes.SETTINGS) {
            SettingsScreen(onBack = { nav.popBackStack() })
        }
    }
}
