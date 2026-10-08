<template>
  <div class="login-page">
    <el-card class="login-card">
      <h2 class="title">语音记事本</h2>
      <el-tabs v-model="mode" stretch>
        <el-tab-pane label="登录" name="login" />
        <el-tab-pane label="注册" name="register" />
      </el-tabs>
      <el-form :model="form" @submit.prevent="submit">
        <el-form-item>
          <el-input v-model="form.username" placeholder="用户名" size="large" />
        </el-form-item>
        <el-form-item>
          <el-input v-model="form.password" type="password" placeholder="密码" size="large" show-password
                    @keyup.enter="submit" />
        </el-form-item>
        <el-button type="primary" size="large" style="width: 100%" :loading="loading" @click="submit">
          {{ mode === 'login' ? '登 录' : '注 册' }}
        </el-button>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '../stores/auth'

const mode = ref('login')
const form = ref({ username: '', password: '' })
const loading = ref(false)
const auth = useAuthStore()
const router = useRouter()

async function submit() {
  if (!form.value.username || !form.value.password) {
    ElMessage.warning('请输入用户名和密码')
    return
  }
  loading.value = true
  try {
    if (mode.value === 'login') {
      await auth.login(form.value.username, form.value.password)
    } else {
      await auth.register(form.value.username, form.value.password)
    }
    router.push('/')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page { min-height: 100vh; display: flex; align-items: center; justify-content: center; }
.login-card { width: 380px; }
.title { text-align: center; margin-bottom: 16px; }
</style>
