package com.voicenotes.data.model

data class Project(
    val id: Int,
    val name: String,
    val note_count: Int,
)

data class Note(
    val id: Int,
    val project_id: Int?,
    val audio_url: String,
    val text: String,
    val duration: Float,
    val sort_order: Int,
    val recorded_at: String,
    val annotations: List<Annotation> = emptyList(),
)

data class Annotation(
    val id: Int,
    val note_id: Int,
    val type: String,
    val content: String,
)

data class AgentJob(
    val job_id: Int,
    val note_id: Int,
    val status: String,
    val app_id: Int? = null,
    val app_name: String? = null,
    val app_url: String? = null,
    val answer: String? = null,
    val error: String? = null,
)

data class AgentTriggerRequest(
    val instruction: String? = null,
    val app_id: Int? = null,
    val app_name: String? = null,
)

data class NoteUpdateRequest(
    val text: String? = null,
    val project_id: Int? = null,
    val sort_order: Int? = null,
)

data class AuthResponse(
    val access_token: String,
    val token_type: String,
)
