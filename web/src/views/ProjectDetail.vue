<template>
  <div class="page">
    <header class="header">
      <div class="left">
        <el-button text @click="router.push('/')">← 返回</el-button>
        <h2>{{ projectName }}</h2>
      </div>
    </header>

    <el-empty v-if="!loading && notes.length === 0" description="这个项目还没有语音记录,请先在 App 端录入" />

    <draggable v-model="notes" item-key="id" handle=".drag-handle" @end="onDragEnd">
      <template #item="{ element: note }">
        <el-card class="note-card" shadow="never">
          <div class="note-main">
            <el-icon class="drag-handle"><Rank /></el-icon>
            <audio :src="note.audio_url" controls preload="none" class="audio" />
            <span class="duration">{{ note.duration.toFixed(1) }}s</span>
            <span class="time">{{ formatTime(note.recorded_at) }}</span>
            <div class="note-actions">
              <el-popconfirm title="确认删除这条记录?" @confirm="removeNote(note)">
                <template #reference>
                  <el-button size="small" text type="danger">删除</el-button>
                </template>
              </el-popconfirm>
            </div>
          </div>

          <div class="note-text">
            <el-input v-model="note.text" type="textarea" :rows="2" placeholder="转写文字(可编辑)"
                      @change="(v) => saveText(note, v)" />
          </div>

          <div class="annotations">
            <div v-for="a in note.annotations" :key="a.id" class="annotation">
              <template v-if="a.type === 'text'">
                <el-tag size="small" type="info">文字</el-tag>
                <span class="annotation-text">{{ a.content }}</span>
              </template>
              <template v-else>
                <el-tag size="small" type="success">图片</el-tag>
                <el-image :src="a.content" fit="cover" class="annotation-img"
                          :preview-src-list="[a.content]" preview-teleported />
              </template>
              <el-button size="small" text type="danger" @click="removeAnnotation(a)">×</el-button>
            </div>

            <div class="annotation-add">
              <el-input v-model="note._newAnnotation" size="small" placeholder="添加文字批注,回车提交"
                        @keyup.enter="addTextAnnotation(note)" style="width: 260px" />
              <el-upload :show-file-list="false" :auto-upload="false" accept="image/*"
                         :on-change="(f) => addImageAnnotation(note, f)">
                <el-button size="small">+ 图片批注</el-button>
              </el-upload>
            </div>
          </div>
        </el-card>
      </template>
    </draggable>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Rank } from '@element-plus/icons-vue'
import draggable from 'vuedraggable'
import { projectApi, noteApi, annotationApi } from '../api'

const route = useRoute()
const router = useRouter()
const projectId = Number(route.params.id)
const projectName = ref('')
const notes = ref([])
const loading = ref(false)

function formatTime(t) {
  return new Date(t).toLocaleString('zh-CN', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

async function load() {
  loading.value = true
  try {
    const list = await projectApi.notes(projectId)
    notes.value = list.map((n) => ({ ...n, _newAnnotation: '' }))
    const projects = await projectApi.list()
    projectName.value = projects.find((p) => p.id === projectId)?.name || '项目'
  } finally {
    loading.value = false
  }
}

async function saveText(note, text) {
  await noteApi.update(note.id, { text })
  ElMessage.success('文字已保存')
}

async function removeNote(note) {
  await noteApi.remove(note.id)
  await load()
}

async function addTextAnnotation(note) {
  const content = note._newAnnotation.trim()
  if (!content) return
  await annotationApi.addText(note.id, content)
  note._newAnnotation = ''
  await load()
}

async function addImageAnnotation(note, uploadFile) {
  await annotationApi.addImage(note.id, uploadFile.raw)
  await load()
}

async function removeAnnotation(a) {
  await annotationApi.remove(a.id)
  await load()
}

async function onDragEnd() {
  // 按新顺序逐个提交 sort_order
  await Promise.all(notes.value.map((n, i) => noteApi.update(n.id, { sort_order: i + 1 })))
}

onMounted(load)
</script>

<style scoped>
.page { max-width: 900px; margin: 0 auto; padding: 24px; }
.header { margin-bottom: 20px; }
.header .left { display: flex; align-items: center; gap: 8px; }
.note-card { margin-bottom: 12px; }
.note-main { display: flex; align-items: center; gap: 12px; margin-bottom: 10px; }
.drag-handle { cursor: grab; color: #c0c4cc; }
.audio { height: 36px; flex: 0 0 280px; }
.duration, .time { font-size: 12px; color: #909399; }
.note-actions { margin-left: auto; }
.annotations { margin-top: 10px; border-top: 1px dashed #e4e7ed; padding-top: 10px; }
.annotation { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.annotation-text { font-size: 13px; color: #606266; }
.annotation-img { width: 80px; height: 80px; border-radius: 4px; }
.annotation-add { display: flex; gap: 8px; align-items: center; margin-top: 4px; }
</style>
