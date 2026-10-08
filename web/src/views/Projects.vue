<template>
  <div class="page">
    <header class="header">
      <h2>我的项目</h2>
      <div>
        <el-button @click="router.push('/organize')">整理语音</el-button>
        <el-button type="primary" @click="openCreate">新建项目</el-button>
        <el-dropdown @command="onUserCmd">
          <span class="username">{{ auth.username }} ▾</span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="logout">退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </header>

    <el-empty v-if="!loading && projects.length === 0" description="还没有项目,点击右上角新建" />

    <el-row :gutter="16">
      <el-col v-for="p in projects" :key="p.id" :xs="24" :sm="12" :md="8" :lg="6">
        <el-card class="project-card" shadow="hover" @click="openProject(p)">
          <div class="card-body">
            <div class="name">{{ p.name }}</div>
            <div class="meta">{{ p.note_count }} 条记录 · {{ formatTime(p.updated_at) }}</div>
          </div>
          <div class="card-actions" @click.stop>
            <el-button size="small" text @click="openRename(p)">重命名</el-button>
            <el-popconfirm title="删除项目将同时删除其下所有记录,确认?" @confirm="removeProject(p)">
              <template #reference>
                <el-button size="small" text type="danger">删除</el-button>
              </template>
            </el-popconfirm>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-dialog v-model="dialog.visible" :title="dialog.isEdit ? '重命名项目' : '新建项目'" width="360px">
      <el-input v-model="dialog.name" placeholder="项目名称" @keyup.enter="submitDialog" />
      <template #footer>
        <el-button @click="dialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="dialog.loading" @click="submitDialog">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { projectApi } from '../api'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()
const projects = ref([])
const loading = ref(false)
const dialog = ref({ visible: false, isEdit: false, id: null, name: '', loading: false })

function formatTime(t) {
  return new Date(t).toLocaleString('zh-CN', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

async function load() {
  loading.value = true
  try {
    projects.value = await projectApi.list()
  } finally {
    loading.value = false
  }
}

function openProject(p) {
  router.push(`/projects/${p.id}`)
}

function openCreate() {
  dialog.value = { visible: true, isEdit: false, id: null, name: '', loading: false }
}

function openRename(p) {
  dialog.value = { visible: true, isEdit: true, id: p.id, name: p.name, loading: false }
}

async function submitDialog() {
  const d = dialog.value
  if (!d.name.trim()) return
  d.loading = true
  try {
    if (d.isEdit) await projectApi.update(d.id, d.name.trim())
    else await projectApi.create(d.name.trim())
    d.visible = false
    await load()
  } finally {
    d.loading = false
  }
}

async function removeProject(p) {
  await projectApi.remove(p.id)
  await load()
}

function onUserCmd(cmd) {
  if (cmd === 'logout') {
    auth.logout()
    router.push('/login')
  }
}

onMounted(load)
</script>

<style scoped>
.page { max-width: 1100px; margin: 0 auto; padding: 24px; }
.header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
.header > div { display: flex; align-items: center; gap: 16px; }
.username { cursor: pointer; color: #606266; }
.project-card { margin-bottom: 16px; cursor: pointer; }
.card-body .name { font-size: 16px; font-weight: 600; margin-bottom: 8px; }
.card-body .meta { font-size: 12px; color: #909399; }
.card-actions { margin-top: 12px; display: flex; gap: 8px; }
</style>
