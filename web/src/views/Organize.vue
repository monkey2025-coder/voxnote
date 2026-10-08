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
        <!-- 选择工具栏:有语音时始终显示,全选 + 计数;有选中时额外显示批量操作 -->
        <div v-if="notes.length" class="batch-bar">
          <el-checkbox :model-value="isAllSelected" :indeterminate="isIndeterminate" @change="toggleAll">
            全选
          </el-checkbox>
          <span class="batch-count">已选 {{ selected.length }} / {{ notes.length }} 条</span>
          <el-button size="small" text @click="invertSelection">反选</el-button>
          <template v-if="selected.length">
            <el-popconfirm title="确认删除选中的语音?此操作不可撤销" @confirm="batchDelete">
              <template #reference>
                <el-button size="small" type="danger">批量删除</el-button>
              </template>
            </el-popconfirm>
            <el-dropdown trigger="click" @command="(t) => batchMove(t)">
              <el-button size="small">批量移动到…</el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item :command="null">📥 未整理</el-dropdown-item>
                  <el-dropdown-item v-for="p in projects" :key="p.id" :command="p.id">📁 {{ p.name }}</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
            <el-button size="small" text @click="clearSelection">取消选择</el-button>
          </template>
        </div>

        <el-empty v-if="notes.length === 0" description="这里没有语音" />
        <el-card v-for="note in notes" :key="note.id" class="note-card" shadow="hover"
                 draggable="true" @dragstart="onDragStart(note)" @dragend="dragging = []; dragOver = null">
          <div class="row">
            <el-checkbox :model-value="selected.includes(note.id)"
                         @change="(v) => toggleSelect(note.id, v)" class="select-box" />
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
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Rank } from '@element-plus/icons-vue'
import { projectApi, noteApi, withToken } from '../api'

const router = useRouter()
const projects = ref([])
const inbox = ref([])
const notes = ref([])          // 当前容器中的语音
const current = ref('inbox')   // 'inbox' 或 projectId
const dragging = ref([])        // 正在拖拽的 note id 列表(支持多选拖拽)
const dragOver = ref(null)
const selected = ref([])       // 选中的 note id 列表

async function load() {
  projects.value = await projectApi.list()
  inbox.value = await noteApi.inbox()
  await select(current.value)
}

async function select(container) {
  current.value = container
  clearSelection()
  if (container === 'inbox') {
    inbox.value = await noteApi.inbox()
    notes.value = inbox.value
  } else {
    notes.value = await projectApi.notes(container)
  }
}

function onDragStart(note) {
  // 文件管理器式拖拽:拖已选中项 → 带上所有选中;拖未选中项 → 只拖这一个并选中它
  if (selected.value.includes(note.id)) {
    dragging.value = [...selected.value]
  } else {
    selected.value = [note.id]
    dragging.value = [note.id]
  }
}

function onNativeDrop(evt, targetProjectId) {
  evt.preventDefault()
  dragOver.value = null
  const ids = [...dragging.value]
  dragging.value = []
  if (ids.length) moveIds(ids, targetProjectId)
}

// 单条"移动到…"按钮:走单条 API(保持原行为)
async function moveNote(note, targetProjectId) {
  if (targetProjectId === note.project_id) return
  await noteApi.update(note.id, { project_id: targetProjectId })
  ElMessage.success(targetProjectId === null ? '已移回未整理' : '已归入项目')
  clearSelection()
  await load()
}

// 多条移动:拖拽和批量移动按钮共用
async function moveIds(ids, targetProjectId) {
  if (!ids.length) return
  await noteApi.batchMove(ids, targetProjectId)
  ElMessage.success(`已移动 ${ids.length} 条到${targetProjectId === null ? '未整理' : '项目'}`)
  clearSelection()
  await load()
}

// ---------- 批量操作 ----------
const isAllSelected = computed(() =>
  notes.value.length > 0 && selected.value.length === notes.value.length
)
const isIndeterminate = computed(() =>
  selected.value.length > 0 && selected.value.length < notes.value.length
)

function toggleAll(checked) {
  selected.value = checked ? notes.value.map((n) => n.id) : []
}

function toggleSelect(id, checked) {
  if (checked) {
    if (!selected.value.includes(id)) selected.value.push(id)
  } else {
    selected.value = selected.value.filter((x) => x !== id)
  }
}

function clearSelection() {
  selected.value = []
}

function invertSelection() {
  const selectedSet = new Set(selected.value)
  selected.value = notes.value.filter((n) => !selectedSet.has(n.id)).map((n) => n.id)
}

async function batchDelete() {
  const ids = [...selected.value]
  await noteApi.batchRemove(ids)
  ElMessage.success(`已删除 ${ids.length} 条`)
  clearSelection()
  await load()
}

async function batchMove(targetProjectId) {
  await moveIds([...selected.value], targetProjectId)
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
.select-box { margin-right: 2px; }
.grip { color: #c0c4cc; }
.audio { height: 32px; flex: 0 0 260px; }
.duration { font-size: 12px; color: #909399; }
.text { margin-top: 8px; font-size: 14px; color: #303133; }
.batch-bar {
  display: flex; align-items: center; gap: 10px;
  margin-bottom: 12px; padding: 10px 14px;
  background: #ecf5ff; border: 1px solid #d9ecff; border-radius: 8px;
}
.batch-count { font-size: 13px; color: #409eff; font-weight: 500; }
</style>
