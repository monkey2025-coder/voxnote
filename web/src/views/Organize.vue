<template>
  <div class="page">
    <header class="header">
      <el-button text @click="router.push('/')">← 返回</el-button>
      <h2>整理语音</h2>
      <span class="hint">把右侧的语音卡片拖到左侧的项目上即可归组,或用卡片上的"移动到…"按钮</span>
    </header>

    <div class="organize">
      <!-- 左侧:项目栏(点击切换视图,也是拖放目标) -->
      <aside class="sidebar">
        <div class="target-row" :class="{ active: current === 'inbox', dragover: dragOver === 'inbox' }"
             @click="select('inbox')"
             @dragover.prevent="dragOver = 'inbox'" @dragleave="dragOver = null" @drop="onNativeDrop($event, null)">
          <span>📥 未整理</span>
          <el-badge :value="inbox.length" type="warning" />
        </div>

        <div v-for="p in projects" :key="p.id" class="target-row"
             :class="{ active: current === p.id, dragover: dragOver === p.id }"
             @click="select(p.id)"
             @dragover.prevent="dragOver = p.id" @dragleave="dragOver = null" @drop="onNativeDrop($event, p.id)">
          <span>📁 {{ p.name }}</span>
          <el-badge :value="p.note_count" type="primary" />
        </div>
      </aside>

      <!-- 右侧:当前容器的语音卡片 -->
      <main class="pool">
        <el-empty v-if="notes.length === 0" description="这里没有语音" />
        <el-card v-for="note in notes" :key="note.id" class="note-card" shadow="hover"
                 draggable="true" @dragstart="dragging = note" @dragend="dragging = null; dragOver = null">
          <div class="row">
            <el-icon class="grip"><Rank /></el-icon>
            <audio :src="withToken(note.audio_url)" controls preload="none" class="audio" />
            <span class="duration">{{ note.duration.toFixed(1) }}s</span>
            <el-dropdown trigger="click" @command="(t) => moveNote(note, t)">
              <el-button size="small">移动到…</el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item :command="null" :disabled="note.project_id === null">📥 未整理</el-dropdown-item>
                  <el-dropdown-item v-for="p in projects" :key="p.id" :command="p.id"
                                    :disabled="note.project_id === p.id">
                    📁 {{ p.name }}
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
          <div class="text">{{ note.text || '(无转写文字)' }}</div>
        </el-card>
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Rank } from '@element-plus/icons-vue'
import { projectApi, noteApi, withToken } from '../api'

const router = useRouter()
const projects = ref([])
const inbox = ref([])
const notes = ref([])          // 当前容器中的语音
const current = ref('inbox')   // 'inbox' 或 projectId
const dragging = ref(null)
const dragOver = ref(null)

async function load() {
  projects.value = await projectApi.list()
  inbox.value = await noteApi.inbox()
  await select(current.value)
}

async function select(container) {
  current.value = container
  if (container === 'inbox') {
    inbox.value = await noteApi.inbox()
    notes.value = inbox.value
  } else {
    notes.value = await projectApi.notes(container)
  }
}

function onNativeDrop(evt, targetProjectId) {
  evt.preventDefault()
  dragOver.value = null
  const note = dragging.value
  dragging.value = null
  if (note) moveNote(note, targetProjectId)
}

async function moveNote(note, targetProjectId) {
  if (targetProjectId === note.project_id) return
  await noteApi.update(note.id, { project_id: targetProjectId })
  ElMessage.success(targetProjectId === null ? '已移回未整理' : '已归入项目')
  await load()
}

onMounted(load)
</script>

<style scoped>
.page { max-width: 1100px; margin: 0 auto; padding: 24px; }
.header { display: flex; align-items: center; gap: 12px; margin-bottom: 20px; }
.hint { color: #909399; font-size: 13px; }
.organize { display: flex; gap: 16px; }
.sidebar { width: 260px; flex-shrink: 0; }
.target-row {
  display: flex; justify-content: space-between; align-items: center;
  padding: 12px 14px; margin-bottom: 10px; cursor: pointer;
  border: 1px dashed #dcdfe6; border-radius: 8px; background: #fff;
}
.target-row.active { border-color: #409eff; background: #ecf5ff; border-style: solid; }
.target-row.dragover { border-color: #67c23a; background: #f0f9eb; border-style: solid; }
.pool { flex: 1; min-height: 200px; }
.note-card { margin-bottom: 10px; cursor: grab; }
.row { display: flex; align-items: center; gap: 10px; }
.grip { color: #c0c4cc; }
.audio { height: 32px; flex: 0 0 260px; }
.duration { font-size: 12px; color: #909399; }
.text { margin-top: 8px; font-size: 14px; color: #303133; }
</style>
