package com.voicenotes.data.repository

import android.content.Context
import com.google.gson.Gson
import com.google.gson.reflect.TypeToken
import com.voicenotes.data.network.ApiClient
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.asRequestBody
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.File

data class PendingUpload(
    val filePath: String,
    val text: String,
    val duration: Float,
    val recordedAt: String,
    val projectId: Int?,
)

/** 简单的 JSON 文件队列:上传失败的语音先落盘,之后自动补传 */
object PendingUploads {
    private val gson = Gson()

    private fun file(context: Context) = File(context.filesDir, "pending_uploads.json")

    suspend fun list(context: Context): MutableList<PendingUpload> = withContext(Dispatchers.IO) {
        val f = file(context)
        if (!f.exists()) return@withContext mutableListOf()
        runCatching {
            val type = object : TypeToken<MutableList<PendingUpload>>() {}.type
            gson.fromJson<MutableList<PendingUpload>>(f.readText(), type) ?: mutableListOf()
        }.getOrDefault(mutableListOf())
    }

    suspend fun add(context: Context, item: PendingUpload) {
        save(context, list(context).apply { add(item) })
    }

    private suspend fun save(context: Context, items: List<PendingUpload>) = withContext(Dispatchers.IO) {
        file(context).writeText(gson.toJson(items))
    }

    /** 尝试补传全部待上传记录,返回剩余数量 */
    suspend fun retryAll(context: Context): Int {
        val items = list(context)
        if (items.isEmpty()) return 0
        val remaining = mutableListOf<PendingUpload>()
        for (item in items) {
            val ok = runCatching { upload(item) }.getOrDefault(false)
            if (ok) {
                File(item.filePath).delete()
            } else {
                remaining.add(item)
            }
        }
        save(context, remaining)
        return remaining.size
    }

    suspend fun upload(item: PendingUpload): Boolean = withContext(Dispatchers.IO) {
        val f = File(item.filePath)
        if (!f.exists()) return@withContext true // 文件丢失,直接丢弃
        val part = MultipartBody.Part.createFormData(
            "file", f.name, f.asRequestBody("audio/mp4".toMediaType())
        )
        val text = item.text.toRequestBody("text/plain".toMediaType())
        val duration = item.duration.toString().toRequestBody("text/plain".toMediaType())
        val recordedAt = item.recordedAt.toRequestBody("text/plain".toMediaType())
        val projectId = item.projectId?.toString()?.toRequestBody("text/plain".toMediaType())
        runCatching {
            ApiClient.notes.upload(part, projectId, text, duration, recordedAt)
        }.isSuccess
    }
}
