package com.voicenotes.data.network

import okhttp3.Interceptor
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Multipart
import retrofit2.http.POST
import retrofit2.http.PUT
import retrofit2.http.Part
import retrofit2.http.Path
import com.voicenotes.data.model.AuthResponse
import com.voicenotes.data.model.Note
import com.voicenotes.data.model.Project
import okhttp3.MultipartBody
import okhttp3.RequestBody

interface AuthApi {
    @POST("/auth/register")
    suspend fun register(@Body body: Map<String, String>): AuthResponse

    @POST("/auth/login")
    suspend fun login(@Body body: Map<String, String>): AuthResponse
}

interface ProjectApi {
    @GET("/projects")
    suspend fun list(): List<Project>

    @GET("/notes/inbox")
    suspend fun inbox(): List<Note>
}

interface NoteApi {
    @Multipart
    @POST("/notes")
    suspend fun upload(
        @Part file: MultipartBody.Part,
        @Part("project_id") projectId: RequestBody?,
        @Part("text") text: RequestBody,
        @Part("duration") duration: RequestBody,
        @Part("recorded_at") recordedAt: RequestBody?,
    ): Note

    @PUT("/notes/{id}")
    suspend fun update(@Path("id") id: Int, @Body body: Map<String, Any?>): Note
}

interface HealthApi {
    @GET("/")
    suspend fun ping(): Map<String, String>
}

object ApiClient {
    const val DEFAULT_URL = "http://10.0.2.2:8000"

    var baseUrl: String = DEFAULT_URL
        private set
    var token: String? = null
        private set

    var auth: AuthApi
        private set
    var projects: ProjectApi
        private set
    var notes: NoteApi
        private set
    var health: HealthApi
        private set

    init {
        val (a, p, n, h) = buildApis(DEFAULT_URL)
        auth = a; projects = p; notes = n; health = h
    }

    /** 切换服务器地址并(可选)更新 token,自动重建全部 API 实例 */
    @Synchronized
    fun configure(newBaseUrl: String? = null, newToken: String? = null) {
        newBaseUrl?.let { baseUrl = it.trimEnd('/') }
        newToken?.let { token = it }
        val (a, p, n, h) = buildApis(baseUrl)
        auth = a; projects = p; notes = n; health = h
    }

    private fun buildApis(url: String): Tuple4 {
        val authInterceptor = Interceptor { chain ->
            val req = chain.request()
            val newReq = if (!token.isNullOrEmpty()) {
                req.newBuilder().header("Authorization", "Bearer $token").build()
            } else req
            chain.proceed(newReq)
        }

        val client = OkHttpClient.Builder()
            .addInterceptor(authInterceptor)
            .addInterceptor(HttpLoggingInterceptor().apply {
                level = HttpLoggingInterceptor.Level.BASIC
            })
            .build()

        val retrofit = Retrofit.Builder()
            .baseUrl(url.trimEnd('/') + "/")
            .client(client)
            .addConverterFactory(GsonConverterFactory.create())
            .build()

        return Tuple4(
            retrofit.create(AuthApi::class.java),
            retrofit.create(ProjectApi::class.java),
            retrofit.create(NoteApi::class.java),
            retrofit.create(HealthApi::class.java),
        )
    }

    private data class Tuple4(
        val first: AuthApi,
        val second: ProjectApi,
        val third: NoteApi,
        val fourth: HealthApi,
    )
}
