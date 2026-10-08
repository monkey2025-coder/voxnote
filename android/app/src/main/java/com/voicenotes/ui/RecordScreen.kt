package com.voicenotes.ui

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.media.MediaRecorder
import android.os.Build
import android.os.Bundle
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
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
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
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
    var text by remember { mutableStateOf("") }
    var partial by remember { mutableStateOf("") }
    var status by remember { mutableStateOf<String?>(null) }
    var uploading by remember { mutableStateOf(false) }
    var speechAvailable by remember { mutableStateOf(true) }
    var recordedAt by remember { mutableStateOf<String?>(null) }

    var recorder by remember { mutableStateOf<MediaRecorder?>(null) }
    var recognizer by remember { mutableStateOf<SpeechRecognizer?>(null) }
    var audioFile by remember { mutableStateOf<File?>(null) }

    fun stopRecording() {
        recognizer?.let { runCatching { it.stopListening(); it.destroy() } }
        recognizer = null
        recorder?.let { runCatching { it.stop(); it.release() } }
        recorder = null
        recording = false
        if (partial.isNotBlank()) {
            text = (text + partial).trim()
            partial = ""
        }
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
        text = ""
        partial = ""
        recordedAt = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss", Locale.US).format(Date())

        if (SpeechRecognizer.isRecognitionAvailable(context)) {
            val sr = SpeechRecognizer.createSpeechRecognizer(context)
            sr.setRecognitionListener(object : RecognitionListener {
                override fun onResults(results: Bundle) {
                    val matches = results.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                    if (!matches.isNullOrEmpty()) text = (text + matches[0]).trim()
                    partial = ""
                }

                override fun onPartialResults(partialResults: Bundle) {
                    val matches = partialResults.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                    partial = matches?.firstOrNull() ?: ""
                }

                override fun onError(error: Int) {
                    partial = ""
                }

                override fun onReadyForSpeech(params: Bundle?) {}
                override fun onBeginningOfSpeech() {}
                override fun onRmsChanged(rmsdB: Float) {}
                override fun onBufferReceived(buffer: ByteArray?) {}
                override fun onEndOfSpeech() {}
                override fun onEvent(eventType: Int, params: Bundle?) {}
            })
            val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
                putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
                putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true)
                putExtra(RecognizerIntent.EXTRA_LANGUAGE, Locale.CHINESE.toLanguageTag())
            }
            sr.startListening(intent)
            recognizer = sr
        } else {
            speechAvailable = false
        }
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
            recognizer?.let { runCatching { it.destroy() } }
            recorder?.let { runCatching { it.release() } }
        }
    }

    Column(
        Modifier
            .fillMaxSize()
            .padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Text(
            if (recording) "录音中…" else "语音记事",
            style = MaterialTheme.typography.headlineSmall,
        )
        Spacer(Modifier.height(8.dp))
        Text(String.format(Locale.US, "%.1f 秒", elapsed), style = MaterialTheme.typography.titleMedium)

        if (!speechAvailable) {
            Spacer(Modifier.height(8.dp))
            Text(
                "当前设备不支持实时语音转写,可录完后手动输入文字",
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                style = MaterialTheme.typography.bodySmall,
            )
        }

        Spacer(Modifier.height(16.dp))
        OutlinedTextField(
            value = text,
            onValueChange = { text = it },
            label = { Text("转写文字(可编辑)") },
            supportingText = if (partial.isNotBlank()) ({ Text(partial) }) else null,
            modifier = Modifier
                .fillMaxWidth()
                .weight(1f),
        )

        if (status != null) {
            Spacer(Modifier.height(8.dp))
            Text(status!!, color = MaterialTheme.colorScheme.primary)
        }

        Spacer(Modifier.height(16.dp))
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            if (!recording) {
                Button(
                    onClick = {
                        if (hasPermission) startRecording() else permLauncher.launch(Manifest.permission.RECORD_AUDIO)
                    },
                    modifier = Modifier.weight(1f),
                    enabled = !uploading,
                ) { Text(if (hasPermission) "开始录音" else "授权麦克风") }

                Button(
                    onClick = {
                        scope.launch {
                            val file = audioFile
                            if (file == null || !file.exists()) {
                                status = "请先录音"
                                return@launch
                            }
                            uploading = true
                            status = null
                            val item = PendingUpload(
                                filePath = file.absolutePath,
                                text = text.trim(),
                                duration = elapsed,
                                recordedAt = recordedAt
                                    ?: SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss", Locale.US).format(Date()),
                                projectId = null,
                            )
                            val ok = runCatching { PendingUploads.upload(item) }.getOrDefault(false)
                            if (ok) {
                                file.delete()
                                status = "已上传"
                                onDone()
                            } else {
                                PendingUploads.add(context, item)
                                status = "网络异常,已保存到本地,稍后自动补传"
                            }
                            uploading = false
                        }
                    },
                    modifier = Modifier.weight(1f),
                    enabled = !uploading && audioFile != null,
                ) { Text(if (uploading) "上传中…" else "保存上传") }

                TextButton(onClick = onDone, enabled = !uploading) { Text("取消") }
            } else {
                Button(
                    onClick = { stopRecording() },
                    modifier = Modifier.weight(1f),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = MaterialTheme.colorScheme.error
                    ),
                ) { Text("停止录音") }
            }
        }
    }
}
