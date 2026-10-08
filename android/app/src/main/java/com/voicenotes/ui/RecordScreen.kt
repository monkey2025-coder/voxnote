package com.voicenotes.ui

import android.Manifest
import android.content.pm.PackageManager
import android.media.MediaRecorder
import android.os.Build
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import com.voicenotes.data.repository.PendingUpload
import com.voicenotes.data.repository.PendingUploads
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

@Composable
fun RecordScreen(onDone: () -> Unit) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()

    var hasPermission by remember {
        mutableStateOf(
            ContextCompat.checkSelfPermission(context, Manifest.permission.RECORD_AUDIO) ==
                PackageManager.PERMISSION_GRANTED
        )
    }
    val permLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { granted -> hasPermission = granted }

    var recording by remember { mutableStateOf(false) }
    var elapsed by remember { mutableFloatStateOf(0f) }
    var status by remember { mutableStateOf<String?>(null) }
    var uploading by remember { mutableStateOf(false) }
    var recordedAt by remember { mutableStateOf<String?>(null) }

    var recorder by remember { mutableStateOf<MediaRecorder?>(null) }
    var audioFile by remember { mutableStateOf<File?>(null) }

    fun stopRecording() {
        recorder?.let { runCatching { it.stop(); it.release() } }
        recorder = null
        recording = false
    }

    fun startRecording() {
        val file = File(context.cacheDir, "rec_${System.currentTimeMillis()}.m4a")
        val r = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            MediaRecorder(context)
        } else {
            @Suppress("DEPRECATION") MediaRecorder()
        }
        r.setAudioSource(MediaRecorder.AudioSource.MIC)
        r.setOutputFormat(MediaRecorder.OutputFormat.MPEG_4)
        r.setAudioEncoder(MediaRecorder.AudioEncoder.AAC)
        r.setAudioEncodingBitRate(128000)
        r.setAudioSamplingRate(44100)
        r.setOutputFile(file.absolutePath)
        r.prepare()
        r.start()
        recorder = r
        audioFile = file
        recording = true
        elapsed = 0f
        recordedAt = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss", Locale.US).format(Date())
    }

    // 计时器
    LaunchedEffect(recording) {
        if (!recording) return@LaunchedEffect
        val start = System.currentTimeMillis()
        while (true) {
            delay(100)
            elapsed = (System.currentTimeMillis() - start) / 1000f
        }
    }

    DisposableEffect(Unit) {
        onDispose {
            recorder?.let { runCatching { it.release() } }
        }
    }

    Column(
        Modifier
            .fillMaxSize()
            .padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
    ) {
        Text(
            if (recording) "正在录音…" else "按住即可录音",
            style = MaterialTheme.typography.headlineSmall,
        )
        Spacer(Modifier.height(16.dp))
        Text(
            String.format(Locale.US, "%.1f 秒", elapsed),
            style = MaterialTheme.typography.displayMedium,
        )
        if (status != null) {
            Spacer(Modifier.height(12.dp))
            Text(status!!, color = MaterialTheme.colorScheme.primary)
        }
        Spacer(Modifier.height(32.dp))

        if (!recording) {
            Button(
                onClick = {
                    if (hasPermission) startRecording() else permLauncher.launch(Manifest.permission.RECORD_AUDIO)
                },
                enabled = !uploading,
                modifier = Modifier.fillMaxWidth(),
            ) { Text(if (hasPermission) "开始录音" else "授权麦克风") }

            Spacer(Modifier.height(12.dp))
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                Button(
                    onClick = {
                        scope.launch {
                            val file = audioFile
                            if (file == null || !file.exists()) {
                                status = "请先录音"
                                return@launch
                            }
                            uploading = true
                            status = "正在上传,文字由服务端自动转写…"
                            val item = PendingUpload(
                                filePath = file.absolutePath,
                                text = "",
                                duration = elapsed,
                                recordedAt = recordedAt
                                    ?: SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss", Locale.US).format(Date()),
                                projectId = null,
                            )
                            val ok = runCatching { PendingUploads.upload(item) }.getOrDefault(false)
                            if (ok) {
                                file.delete()
                                audioFile = null
                                onDone()
                            } else {
                                PendingUploads.add(context, item)
                                status = "网络异常,已保存到本地,稍后自动补传"
                                uploading = false
                            }
                        }
                    },
                    modifier = Modifier.weight(1f),
                    enabled = !uploading && audioFile != null,
                ) { Text(if (uploading) "上传中…" else "保存并上传") }

                androidx.compose.material3.TextButton(
                    onClick = onDone,
                    enabled = !uploading,
                ) { Text("取消") }
            }
        } else {
            Button(
                onClick = { stopRecording() },
                modifier = Modifier.fillMaxWidth(),
                colors = ButtonDefaults.buttonColors(
                    containerColor = MaterialTheme.colorScheme.error
                ),
            ) { Text("停止录音") }
        }
    }
}
