package com.voicenotes.data.repository

import android.content.Context
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import com.voicenotes.data.network.ApiClient

private val Context.dataStore by preferencesDataStore("voicenotes")

object TokenStore {
    private val TOKEN_KEY = stringPreferencesKey("token")
    private val USER_KEY = stringPreferencesKey("username")
    private val SERVER_KEY = stringPreferencesKey("server_url")

    fun tokenFlow(context: Context): Flow<String?> =
        context.dataStore.data.map { it[TOKEN_KEY] }

    fun usernameFlow(context: Context): Flow<String?> =
        context.dataStore.data.map { it[USER_KEY] }

    fun serverFlow(context: Context): Flow<String> =
        context.dataStore.data.map { it[SERVER_KEY] ?: ApiClient.DEFAULT_URL }

    suspend fun save(context: Context, token: String, username: String) {
        context.dataStore.edit {
            it[TOKEN_KEY] = token
            it[USER_KEY] = username
        }
    }

    suspend fun saveServer(context: Context, url: String) {
        context.dataStore.edit { it[SERVER_KEY] = url.trimEnd('/') }
    }

    suspend fun clear(context: Context) {
        context.dataStore.edit {
            it.remove(TOKEN_KEY)
            it.remove(USER_KEY)
        }
    }
}
