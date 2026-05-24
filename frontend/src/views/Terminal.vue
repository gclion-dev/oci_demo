<template>
  <div class="h-screen w-screen flex flex-col bg-surface-50 dark:bg-surface-900 overflow-hidden">
    <!-- Top bar -->
    <div class="flex items-center gap-3 px-4 py-2 bg-white dark:bg-surface-800 border-b border-surface-200 dark:border-surface-700 shrink-0">
      <span class="font-semibold text-surface-900 dark:text-white text-sm">
        {{ sshInfo.consoleMode ? 'OCI 串行控制台' : `SSH — ${sshInfo.username}@${sshInfo.host}:${sshInfo.port}` }}
      </span>
      <span :class="connected ? 'badge-success' : 'badge-danger'" class="text-xs">{{ connected ? '已连接' : '未连接' }}</span>
      <span v-if="sysInfo.hostname" class="text-xs text-surface-500">({{ sysInfo.hostname }})</span>
      <div class="flex-1"></div>
      <span v-if="!sshInfo.consoleMode" class="text-xs text-surface-400">运行 {{ formatUptime(sysInfo.uptime_seconds) }}</span>
    </div>

    <!-- Main content -->
    <div class="flex flex-1 overflow-hidden">
      <!-- Left panel: System Info -->
      <div class="w-72 shrink-0 border-r border-surface-200 dark:border-surface-700 overflow-y-auto bg-white dark:bg-surface-800 p-3 space-y-3 text-xs">
        <!-- CPU & Memory -->
        <div class="space-y-2">
          <h3 class="font-semibold text-surface-700 dark:text-surface-300 text-xs uppercase tracking-wide">系统信息</h3>
          <div class="space-y-1.5">
            <!-- CPU -->
            <div>
              <div class="flex justify-between mb-0.5">
                <span class="text-surface-500">CPU ({{ sysInfo.cpu_cores }}核)</span>
                <span class="text-surface-800 dark:text-surface-200">{{ sysInfo.cpu_percent }}%</span>
              </div>
              <div class="h-2 bg-surface-200 dark:bg-surface-700 rounded-full overflow-hidden">
                <div class="h-full bg-blue-500 transition-all duration-500" :style="{ width: sysInfo.cpu_percent + '%' }"></div>
              </div>
            </div>
            <!-- Memory -->
            <div>
              <div class="flex justify-between mb-0.5">
                <span class="text-surface-500">内存</span>
                <span class="text-surface-800 dark:text-surface-200">{{ formatBytes(sysInfo.memory.used) }}/{{ formatBytes(sysInfo.memory.total) }}</span>
              </div>
              <div class="h-2 bg-surface-200 dark:bg-surface-700 rounded-full overflow-hidden">
                <div class="h-full bg-emerald-500 transition-all duration-500" :style="{ width: sysInfo.memory.percent + '%' }"></div>
              </div>
            </div>
            <!-- Swap -->
            <div>
              <div class="flex justify-between mb-0.5">
                <span class="text-surface-500">交换</span>
                <span class="text-surface-800 dark:text-surface-200">{{ formatBytes(sysInfo.swap.used) }}/{{ formatBytes(sysInfo.swap.total) }}</span>
              </div>
              <div class="h-2 bg-surface-200 dark:bg-surface-700 rounded-full overflow-hidden">
                <div class="h-full bg-amber-500 transition-all duration-500" :style="{ width: sysInfo.swap.percent + '%' }"></div>
              </div>
            </div>
          </div>
        </div>

        <hr class="border-surface-200 dark:border-surface-600" />

        <!-- Processes -->
        <div class="space-y-1.5">
          <h3 class="font-semibold text-surface-700 dark:text-surface-300 text-xs uppercase tracking-wide">进程 (Top 4)</h3>
          <table class="w-full text-[11px] rounded overflow-hidden">
            <thead>
              <tr class="text-white text-[11px]">
                <th class="text-right pr-2 py-0.5 bg-blue-600 rounded-tl">内存</th>
                <th class="text-right pr-2 py-0.5 bg-red-500">CPU</th>
                <th class="text-left pl-2 py-0.5 bg-blue-600 rounded-tr">命令</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(proc, i) in sysInfo.processes" :key="i" :class="[i % 2 === 0 ? 'bg-blue-50 dark:bg-blue-900/20' : 'bg-blue-100/50 dark:bg-blue-900/40', i === sysInfo.processes.length - 1 ? 'last-row' : '']" class="text-surface-700 dark:text-surface-300">
                <td class="text-right pr-2 py-0.5" :class="i === sysInfo.processes.length - 1 ? 'rounded-bl' : ''">{{ formatBytes(proc.rss) }}</td>
                <td class="text-right pr-2 py-0.5">{{ proc.cpu }}</td>
                <td class="text-left pl-2 py-0.5 truncate max-w-[100px]" :class="i === sysInfo.processes.length - 1 ? 'rounded-br' : ''">{{ proc.command }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <hr class="border-surface-200 dark:border-surface-600" />

        <!-- Network -->
        <div class="space-y-1.5">
          <h3 class="font-semibold text-surface-700 dark:text-surface-300 text-xs uppercase tracking-wide">网络流量</h3>
          <div v-for="iface in sysInfo.network" :key="iface.interface">
            <div class="flex items-center justify-between mb-0.5">
              <span class="font-medium text-surface-700 dark:text-surface-300">{{ iface.interface }}</span>
            </div>
            <div class="flex justify-between text-[10px] mb-1">
              <span class="text-orange-500 font-medium">↑ {{ formatRate(iface.tx_rate) }}</span>
              <span class="text-blue-500 font-medium">↓ {{ formatRate(iface.rx_rate) }}</span>
            </div>
            <!-- Bar chart with Y-axis inside -->
            <div class="relative h-20 border border-surface-200 dark:border-surface-700 rounded bg-white dark:bg-surface-900 p-1">
              <span class="absolute top-0.5 left-1 text-[9px] text-surface-400 z-10">{{ getNetMax(iface.interface) }}</span>
              <div class="h-full flex items-end gap-[1px]">
                <div v-for="(sample, si) in getNetHistory(iface.interface)" :key="si" class="flex-1 flex items-end gap-[0.5px] h-full">
                  <div class="flex-1 bg-orange-300 dark:bg-orange-400 rounded-t-sm min-w-0" :style="{ height: sample.txPct + '%' }"></div>
                  <div class="flex-1 bg-blue-300 dark:bg-blue-400 rounded-t-sm min-w-0" :style="{ height: sample.rxPct + '%' }"></div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <hr class="border-surface-200 dark:border-surface-600" />

        <!-- Ping -->
        <div class="space-y-1.5">
          <div class="flex items-center justify-between">
            <h3 class="font-semibold text-surface-700 dark:text-surface-300 text-xs uppercase tracking-wide">Ping</h3>
            <span class="text-xs font-medium" :class="currentPing < 0 ? 'text-red-500' : 'text-emerald-600'">
              {{ currentPing < 0 ? '超时' : currentPing.toFixed(1) + 'ms' }}
            </span>
          </div>
          <div class="relative h-14 border border-surface-200 dark:border-surface-700 rounded bg-white dark:bg-surface-900 p-1">
            <span class="absolute top-0.5 left-1 text-[9px] text-surface-400 z-10">{{ getPingMax() }}</span>
            <div class="h-full flex items-end gap-[1px]">
              <div v-for="(sample, si) in getPingHistory()" :key="si" class="flex-1 flex items-end h-full">
                <div v-if="!sample.lost" class="flex-1 bg-emerald-400 dark:bg-emerald-500 rounded-t-sm" :style="{ height: sample.pct + '%' }"></div>
              </div>
            </div>
          </div>
        </div>

        <hr class="border-surface-200 dark:border-surface-600" />

        <!-- Disks -->
        <div class="space-y-1.5">
          <h3 class="font-semibold text-surface-700 dark:text-surface-300 text-xs uppercase tracking-wide">磁盘</h3>
          <div v-for="disk in sysInfo.disks" :key="disk.mount" class="space-y-0.5">
            <div class="flex justify-between text-surface-500">
              <span class="truncate max-w-[100px]">{{ disk.mount }}</span>
              <span>{{ formatBytes(disk.used) }}/{{ formatBytes(disk.total) }}</span>
            </div>
            <div class="h-1.5 bg-surface-200 dark:bg-surface-700 rounded-full overflow-hidden">
              <div class="h-full bg-violet-500 transition-all duration-500" :style="{ width: (disk.total > 0 ? disk.used / disk.total * 100 : 0) + '%' }"></div>
            </div>
          </div>
        </div>
      </div>

      <!-- Right panel -->
      <div class="flex-1 flex flex-col overflow-hidden">
        <!-- Terminal -->
        <div class="flex-1 overflow-hidden" :style="{ flexBasis: terminalHeight }">
          <div ref="terminalRef" class="h-full bg-[#0f172a]"></div>
        </div>

        <!-- Resizer -->
        <div class="h-1 bg-surface-200 dark:bg-surface-700 cursor-row-resize hover:bg-primary-400 transition-colors shrink-0" @mousedown="startResize"></div>

        <!-- File Manager / Commands Panel -->
        <div class="overflow-hidden bg-white dark:bg-surface-800 flex flex-col" :style="{ height: fileManagerHeight }">
          <!-- Tabs -->
          <div class="flex items-center border-b border-surface-200 dark:border-surface-700 text-xs shrink-0">
            <button class="px-4 py-2 font-medium border-b-2 transition-colors"
              :class="bottomTab === 'files' ? 'text-primary-600 border-primary-600' : 'text-surface-500 border-transparent hover:text-surface-700'"
              @click="bottomTab = 'files'">文件</button>
            <button class="px-4 py-2 font-medium border-b-2 transition-colors"
              :class="bottomTab === 'commands' ? 'text-primary-600 border-primary-600' : 'text-surface-500 border-transparent hover:text-surface-700'"
              @click="bottomTab = 'commands'; loadQuickCommands()">命令</button>
            <!-- File toolbar (only when files tab active) -->
            <template v-if="bottomTab === 'files'">
              <span class="text-surface-600 dark:text-surface-400 flex-1 truncate px-2">{{ currentPath }}</span>
              <button class="text-surface-500 hover:text-surface-800 dark:hover:text-white px-1.5" @click="goParent" title="上级目录">⬆</button>
              <button class="text-surface-500 hover:text-surface-800 dark:hover:text-white px-1.5" @click="refreshFiles" title="刷新">⟳</button>
              <button class="text-surface-500 hover:text-surface-800 dark:hover:text-white px-1.5 mr-2" @click="doMkdir" title="新建文件夹">📁+</button>
            </template>
          </div>

          <!-- Files Tab Content -->
          <div v-show="bottomTab === 'files'" class="flex flex-1 overflow-hidden">
            <!-- Directory tree (left) -->
            <div class="w-44 border-r border-surface-200 dark:border-surface-700 overflow-y-auto text-xs shrink-0">
              <div class="p-1">
                <!-- Root node -->
                <div class="flex items-center gap-1 px-2 py-1 rounded cursor-pointer hover:bg-surface-100 dark:hover:bg-surface-700"
                  :class="{ 'bg-blue-50 dark:bg-blue-900/30': currentPath === '/' }"
                  @click="loadFiles('/')">
                  <span>📁</span>
                  <span class="text-surface-700 dark:text-surface-300 font-medium">/</span>
                </div>
                <!-- Tree nodes -->
                <div v-for="node in treeNodes" :key="node.path" class="ml-2">
                  <div class="flex items-center gap-1 px-2 py-0.5 rounded cursor-pointer hover:bg-surface-100 dark:hover:bg-surface-700"
                    :class="{ 'bg-blue-50 dark:bg-blue-900/30': currentPath === node.path }"
                    @click="onTreeNodeClick(node)">
                    <span class="text-[10px] w-3 text-center">{{ node.expanded ? '▼' : '▶' }}</span>
                    <span>📁</span>
                    <span class="truncate text-surface-700 dark:text-surface-300">{{ node.name }}</span>
                  </div>
                  <!-- Children -->
                  <div v-if="node.expanded && node.children.length > 0" class="ml-3">
                    <div v-for="child in node.children" :key="child.path"
                      class="flex items-center gap-1 px-2 py-0.5 rounded cursor-pointer hover:bg-surface-100 dark:hover:bg-surface-700"
                      :class="{ 'bg-blue-50 dark:bg-blue-900/30': currentPath === child.path }"
                      @click="onTreeNodeClick(child)">
                      <span class="text-[10px] w-3 text-center">{{ child.expanded ? '▼' : '▶' }}</span>
                      <span>📁</span>
                      <span class="truncate text-surface-700 dark:text-surface-300">{{ child.name }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- File table (right) -->
            <div class="flex-1 overflow-y-auto">
              <table class="w-full text-xs table-fixed">
                <thead class="sticky top-0 bg-surface-50 dark:bg-surface-800 z-10">
                  <tr class="text-surface-400 border-b border-surface-200 dark:border-surface-700">
                    <th class="text-left px-2 py-1.5 cursor-col-resize" :style="{ width: colWidths.name + 'px' }">文件名</th>
                    <th class="text-right px-2 py-1.5 cursor-col-resize" :style="{ width: colWidths.size + 'px' }">大小</th>
                    <th class="text-left px-2 py-1.5 cursor-col-resize" :style="{ width: colWidths.type + 'px' }">类型</th>
                    <th class="text-right px-2 py-1.5 cursor-col-resize" :style="{ width: colWidths.mtime + 'px' }">修改时间</th>
                    <th class="text-center px-2 py-1.5 cursor-col-resize" :style="{ width: colWidths.perm + 'px' }">权限</th>
                    <th class="text-center px-2 py-1.5" style="width: 40px">操作</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="file in fileList" :key="file.name"
                    class="border-b border-surface-100 dark:border-surface-700/50 hover:bg-surface-50 dark:hover:bg-surface-700/30"
                    :class="{ 'cursor-pointer': file.is_dir }"
                    @dblclick="file.is_dir && enterDir(file.name)">
                    <td class="px-2 py-1 text-surface-800 dark:text-surface-200 truncate">
                      <span class="mr-1">{{ file.is_dir ? '📁' : '📄' }}</span>{{ file.name }}
                    </td>
                    <td class="text-right px-2 py-1 text-surface-500">{{ file.is_dir ? '' : formatBytes(file.size) }}</td>
                    <td class="px-2 py-1 text-surface-500">{{ file.is_dir ? '文件夹' : getFileType(file.name) }}</td>
                    <td class="text-right px-2 py-1 text-surface-500">{{ formatTimestamp(file.mtime) }}</td>
                    <td class="text-center px-2 py-1 text-surface-500 font-mono text-[10px]">{{ file.permissions }}</td>
                    <td class="text-center px-2 py-1 relative">
                      <button class="text-surface-500 hover:text-surface-800 dark:hover:text-white" @click.stop="toggleFileMenu(file)">⋯</button>
                      <!-- Dropdown menu -->
                      <div v-if="activeFileMenu === file.name" class="absolute right-0 top-full mt-0.5 w-24 bg-white dark:bg-surface-800 border border-surface-200 dark:border-surface-700 rounded shadow-lg py-0.5 z-20 text-left">
                        <button v-if="!file.is_dir" class="w-full text-left px-3 py-1 text-xs hover:bg-surface-100 dark:hover:bg-surface-700 text-surface-700 dark:text-surface-300" @click="doDownload(file); activeFileMenu = null">下载</button>
                        <button class="w-full text-left px-3 py-1 text-xs hover:bg-surface-100 dark:hover:bg-surface-700 text-red-600 dark:text-red-400" @click="doDelete(file); activeFileMenu = null">删除</button>
                      </div>
                    </td>
                  </tr>
                </tbody>
              </table>
              <div v-if="fileLoading" class="text-center text-surface-400 py-4 text-xs">加载中...</div>
              <div v-if="!fileLoading && fileList.length === 0" class="text-center text-surface-400 py-4 text-xs">空目录</div>
            </div>
          </div>

          <!-- Commands Tab Content -->
          <div v-show="bottomTab === 'commands'" class="flex-1 flex flex-col overflow-hidden">
            <!-- Category tabs -->
            <div class="flex items-center gap-1 px-3 py-1.5 border-b border-surface-200 dark:border-surface-700 overflow-x-auto shrink-0">
              <button v-for="cat in cmdCategories" :key="cat"
                class="px-2.5 py-1 rounded text-xs whitespace-nowrap transition-colors"
                :class="activeCmdCategory === cat ? 'bg-primary-100 dark:bg-primary-900/40 text-primary-700 dark:text-primary-300 font-medium' : 'text-surface-500 hover:bg-surface-100 dark:hover:bg-surface-700'"
                @click="activeCmdCategory = cat">
                {{ cat }}
              </button>
              <button class="px-2 py-1 rounded text-xs text-surface-400 hover:text-surface-700 dark:hover:text-white hover:bg-surface-100 dark:hover:bg-surface-700" @click="addCategory" title="新建分类">+</button>
            </div>
            <!-- Command buttons area (scrollable) -->
            <div class="flex-1 overflow-y-auto p-3">
              <div class="flex flex-wrap gap-2">
                <button v-for="(cmd, idx) in filteredCommands" :key="cmd.id"
                  draggable="true"
                  class="inline-flex items-center gap-1 px-3 py-1.5 bg-surface-100 dark:bg-surface-700 hover:bg-surface-200 dark:hover:bg-surface-600 rounded text-xs text-surface-700 dark:text-surface-300 transition-colors cursor-grab active:cursor-grabbing"
                  :class="{ 'ring-2 ring-primary-400': dragOverIdx === idx }"
                  @click="executeQuickCommand(cmd)"
                  @dragstart="onCmdDragStart(idx, $event)"
                  @dragover.prevent="onCmdDragOver(idx)"
                  @dragleave="dragOverIdx = -1"
                  @drop.prevent="onCmdDrop(idx)"
                  @dragend="dragOverIdx = -1">
                  {{ cmd.name }}
                  <span class="text-surface-400 hover:text-red-500 ml-1" @click.stop="deleteQuickCommand(cmd)" title="删除">×</span>
                </button>
              </div>
              <div v-if="filteredCommands.length === 0" class="text-center text-surface-400 text-xs py-6">该分类暂无命令</div>
            </div>
            <!-- Bottom bar: add + import/export -->
            <div class="flex items-center gap-2 px-3 py-2 border-t border-surface-200 dark:border-surface-700 shrink-0">
              <input v-model="newCmdName" class="input text-xs flex-shrink-0 w-20" placeholder="名称" />
              <input v-model="newCmdCommand" class="input text-xs flex-1" placeholder="命令，如: git pull" @keyup.enter="addQuickCommand" />
              <button class="btn-primary btn-sm text-xs whitespace-nowrap" @click="addQuickCommand">添加</button>
              <span class="text-surface-300 mx-1">|</span>
              <button class="btn-ghost btn-sm text-xs whitespace-nowrap" @click="exportCommands" title="导出命令">导出</button>
              <button class="btn-ghost btn-sm text-xs whitespace-nowrap" @click="triggerImport" title="导入命令">导入</button>
              <input ref="importFileRef" type="file" accept=".json" class="hidden" @change="importCommands" />
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useToast } from '@/composables/useToast'
import { Terminal } from '@xterm/xterm'
import { FitAddon } from '@xterm/addon-fit'
import '@xterm/xterm/css/xterm.css'
import api from '@/api'
import dayjs from 'dayjs'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const { success, error: showError, warning } = useToast()

// Auth guard
if (!auth.token) { router.replace('/login') }

// 从 localStorage 读取连接参数
const sk = route.query.sk as string
const raw = sk ? localStorage.getItem(sk) : null
if (sk) localStorage.removeItem(sk)
const sshInfo = reactive(raw ? JSON.parse(raw) : { host: '', port: 22, username: 'root', authType: 'password', password: '', privateKey: '', tenantId: 0 })

// ─── Terminal ────────────────────────────────────────────────────────────────
const terminalRef = ref<HTMLElement | null>(null)
const connected = ref(false)
let terminal: Terminal | null = null
let fitAddon: FitAddon | null = null
let ws: WebSocket | null = null
let resizeObserver: ResizeObserver | null = null

// ─── System Info ─────────────────────────────────────────────────────────────
const sysInfo = reactive({
  hostname: '',
  uptime_seconds: 0,
  load_avg: [0, 0, 0],
  cpu_cores: 1,
  cpu_percent: 0,
  memory: { total: 0, used: 0, free: 0, percent: 0 },
  swap: { total: 0, used: 0, free: 0, percent: 0 },
  network: [] as any[],
  disks: [] as any[],
  processes: [] as any[],
})
let monitorWs: WebSocket | null = null

// Network history for bar chart (last 30 samples per interface, 1s interval)
const NET_HISTORY_LEN = 30
const netHistory = reactive<Record<string, { rx: number; tx: number }[]>>({})

function getNetHistory(iface: string): { rxPct: number; txPct: number }[] {
  const history = netHistory[iface] || []
  // Find max value for scaling, minimum 1KB to avoid division by zero
  let maxVal = 1024
  for (const s of history) {
    if (s.rx > maxVal) maxVal = s.rx
    if (s.tx > maxVal) maxVal = s.tx
  }
  // Pad to NET_HISTORY_LEN
  const padded: { rx: number; tx: number }[] = []
  for (let i = 0; i < NET_HISTORY_LEN - history.length; i++) padded.push({ rx: 0, tx: 0 })
  for (const s of history) padded.push(s)
  return padded.map(s => ({
    rxPct: Math.round((s.rx / maxVal) * 100),
    txPct: Math.round((s.tx / maxVal) * 100),
  }))
}

function getNetMax(iface: string): string {
  const history = netHistory[iface] || []
  let maxVal = 0
  for (const s of history) {
    if (s.rx > maxVal) maxVal = s.rx
    if (s.tx > maxVal) maxVal = s.tx
  }
  return formatBytes(maxVal)
}

function updateNetHistory(network: any[]) {
  for (const iface of network) {
    if (!netHistory[iface.interface]) netHistory[iface.interface] = []
    netHistory[iface.interface].push({ rx: iface.rx_rate || 0, tx: iface.tx_rate || 0 })
    if (netHistory[iface.interface].length > NET_HISTORY_LEN) {
      netHistory[iface.interface].shift()
    }
  }
}

// Ping history (last 30 samples, -1 = packet loss)
const PING_HISTORY_LEN = 30
const pingHistory = reactive<number[]>([])
const currentPing = ref<number>(-1)

function updatePingHistory(pingMs: number) {
  currentPing.value = pingMs
  pingHistory.push(pingMs)
  if (pingHistory.length > PING_HISTORY_LEN) pingHistory.shift()
}

function getPingHistory(): { pct: number; lost: boolean }[] {
  // Find max ping for scaling (minimum 10ms)
  let maxVal = 10
  for (const p of pingHistory) {
    if (p > maxVal) maxVal = p
  }
  const padded: number[] = []
  for (let i = 0; i < PING_HISTORY_LEN - pingHistory.length; i++) padded.push(-1)
  for (const p of pingHistory) padded.push(p)
  return padded.map(p => ({
    pct: p < 0 ? 0 : Math.max(2, Math.round((p / maxVal) * 100)),
    lost: p < 0,
  }))
}

function getPingMax(): string {
  let maxVal = 0
  for (const p of pingHistory) {
    if (p > maxVal) maxVal = p
  }
  return maxVal > 0 ? Math.round(maxVal) + 'ms' : '-'
}

// ─── File Manager ────────────────────────────────────────────────────────────
const bottomTab = ref('files')
const currentPath = ref('/')
const fileList = ref<any[]>([])
const fileLoading = ref(false)
const activeFileMenu = ref<string | null>(null)
const colWidths = reactive({ name: 180, size: 70, type: 60, mtime: 110, perm: 80 })

// Tree state
interface TreeNode { name: string; path: string; expanded: boolean; children: TreeNode[] }
const treeNodes = ref<TreeNode[]>([])

function getFileType(name: string): string {
  const ext = name.split('.').pop()?.toLowerCase() || ''
  const types: Record<string, string> = {
    txt: '文本', log: '日志', json: 'JSON', yml: 'YAML', yaml: 'YAML',
    py: 'Python', js: 'JS', ts: 'TS', sh: 'Shell', conf: '配置',
    gz: '压缩包', tar: '归档', zip: '压缩包', png: '图片', jpg: '图片',
  }
  return types[ext] || ext || '文件'
}

function toggleFileMenu(file: any) {
  activeFileMenu.value = activeFileMenu.value === file.name ? null : file.name
}

// Close file menu on outside click
function onFileMenuOutsideClick(e: MouseEvent) {
  if (activeFileMenu.value) activeFileMenu.value = null
}

// ─── Quick Commands ──────────────────────────────────────────────────────────
const quickCommands = ref<any[]>([])
const newCmdName = ref('')
const newCmdCommand = ref('')
const importFileRef = ref<HTMLInputElement | null>(null)
const dragStartIdx = ref(-1)
const dragOverIdx = ref(-1)
const activeCmdCategory = ref('默认分类')

const cmdCategories = computed(() => {
  const cats = new Set<string>()
  for (const cmd of quickCommands.value) cats.add(cmd.category || '默认分类')
  if (cats.size === 0) cats.add('默认分类')
  return Array.from(cats)
})

const filteredCommands = computed(() => {
  return quickCommands.value.filter(c => (c.category || '默认分类') === activeCmdCategory.value)
})

function addCategory() {
  const name = prompt('新分类名称:')
  if (!name) return
  activeCmdCategory.value = name
}

function onCmdDragStart(idx: number, e: DragEvent) {
  dragStartIdx.value = idx
  if (e.dataTransfer) e.dataTransfer.effectAllowed = 'move'
}

function onCmdDragOver(idx: number) {
  dragOverIdx.value = idx
}

async function onCmdDrop(targetIdx: number) {
  dragOverIdx.value = -1
  const fromIdx = dragStartIdx.value
  if (fromIdx === targetIdx || fromIdx < 0) return

  // Reorder within filtered list
  const items = [...filteredCommands.value]
  const [moved] = items.splice(fromIdx, 1)
  items.splice(targetIdx, 0, moved)

  // Update sort_order for items in this category
  try {
    for (let i = 0; i < items.length; i++) {
      if (items[i].sort_order !== i) {
        await api.put(`/quick-commands/${items[i].id}`, { sort_order: i })
      }
    }
    loadQuickCommands()
  } catch { /* ignore */ }
}

async function loadQuickCommands() {
  try {
    const res = await api.get('/quick-commands')
    quickCommands.value = res.data
  } catch { /* ignore */ }
}

async function addQuickCommand() {
  if (!newCmdName.value || !newCmdCommand.value) { warning('请填写名称和命令'); return }
  try {
    await api.post('/quick-commands', { name: newCmdName.value, command: newCmdCommand.value, category: activeCmdCategory.value })
    newCmdName.value = ''
    newCmdCommand.value = ''
    loadQuickCommands()
    success('命令已添加')
  } catch { /* ignore */ }
}

async function deleteQuickCommand(cmd: any) {
  if (!confirm(`删除快捷命令「${cmd.name}」？`)) return
  try {
    await api.delete(`/quick-commands/${cmd.id}`)
    loadQuickCommands()
  } catch { /* ignore */ }
}

function executeQuickCommand(cmd: any) {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(cmd.command + '\n')
    success(`已发送: ${cmd.name}`)
  } else {
    showError('终端未连接')
  }
}

function exportCommands() {
  const data = quickCommands.value.map(c => ({ name: c.name, command: c.command, category: c.category }))
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'quick-commands.json'
  a.click()
  URL.revokeObjectURL(url)
}

function triggerImport() {
  importFileRef.value?.click()
}

async function importCommands(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  try {
    const text = await file.text()
    const data = JSON.parse(text)
    if (!Array.isArray(data)) { showError('文件格式错误'); return }
    let count = 0
    for (const item of data) {
      if (item.name && item.command) {
        await api.post('/quick-commands', { name: item.name, command: item.command, category: item.category || '默认分类' })
        count++
      }
    }
    success(`已导入 ${count} 条命令`)
    loadQuickCommands()
  } catch {
    showError('导入失败，请检查文件格式')
  }
  // Reset file input
  if (importFileRef.value) importFileRef.value.value = ''
}

// ─── Layout resize ──────────────────────────────────────────────────────────
const terminalHeight = ref('60%')
const fileManagerHeight = ref('40%')
let isResizing = false

function startResize(e: MouseEvent) {
  isResizing = true
  const startY = e.clientY
  const container = (e.target as HTMLElement).parentElement!
  const containerRect = container.getBoundingClientRect()
  const totalHeight = containerRect.height

  const onMove = (ev: MouseEvent) => {
    if (!isResizing) return
    const offset = ev.clientY - containerRect.top
    const pct = Math.max(20, Math.min(80, (offset / totalHeight) * 100))
    terminalHeight.value = pct + '%'
    fileManagerHeight.value = (100 - pct) + '%'
    fitAddon?.fit()
  }
  const onUp = () => {
    isResizing = false
    document.removeEventListener('mousemove', onMove)
    document.removeEventListener('mouseup', onUp)
    fitAddon?.fit()
  }
  document.addEventListener('mousemove', onMove)
  document.addEventListener('mouseup', onUp)
}

// ─── Helpers ─────────────────────────────────────────────────────────────────
function formatBytes(bytes: number): string {
  if (!bytes || bytes === 0) return '0'
  const units = ['B', 'K', 'M', 'G', 'T']
  let i = 0
  let val = bytes
  while (val >= 1024 && i < units.length - 1) { val /= 1024; i++ }
  return val.toFixed(i > 0 ? 1 : 0) + units[i]
}

function formatRate(bytesPerSec: number): string {
  if (!bytesPerSec) return '0B/s'
  return formatBytes(bytesPerSec) + '/s'
}

function formatUptime(seconds: number): string {
  if (!seconds) return '-'
  const d = Math.floor(seconds / 86400)
  const h = Math.floor((seconds % 86400) / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  if (d > 0) return `${d}天${h}时`
  if (h > 0) return `${h}时${m}分`
  return `${m}分`
}

function formatTimestamp(ts: number): string {
  if (!ts) return '-'
  return dayjs.unix(ts).format('MM-DD HH:mm')
}

// ─── Terminal WebSocket ──────────────────────────────────────────────────────
function getWsUrl() {
  const token = localStorage.getItem('token')
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const baseHost = window.location.host
  const params = new URLSearchParams({
    token: token || '',
    host: sshInfo.host,
    port: String(sshInfo.port),
    username: sshInfo.username,
    auth_type: sshInfo.authType,
    tenant_id: String(sshInfo.tenantId),
  })
  return `${protocol}//${baseHost}/api/terminal/ws?${params.toString()}`
}

function getConsoleWsUrl() {
  const token = localStorage.getItem('token')
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const baseHost = window.location.host
  const params = new URLSearchParams({ token: token || '' })
  return `${protocol}//${baseHost}/api/terminal/ws/console?${params.toString()}`
}

function getMonitorWsUrl() {
  const token = localStorage.getItem('token')
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const baseHost = window.location.host
  const params = new URLSearchParams({
    token: token || '',
    host: sshInfo.host,
    port: String(sshInfo.port),
    username: sshInfo.username,
    auth_type: sshInfo.authType,
  })
  return `${protocol}//${baseHost}/api/terminal-monitor/ws/monitor?${params.toString()}`
}

function initTerminal() {
  terminal = new Terminal({
    cursorBlink: true,
    fontSize: 13,
    fontFamily: "'JetBrains Mono', 'Fira Code', 'Courier New', monospace",
    theme: { background: '#0f172a', foreground: '#e2e8f0', cursor: '#a78bfa', selectionBackground: '#334155' },
    scrollback: 5000,
  })
  fitAddon = new FitAddon()
  terminal.loadAddon(fitAddon)
  terminal.open(terminalRef.value!)
  nextTick(() => fitAddon!.fit())

  terminal.onData((data) => {
    if (ws && ws.readyState === WebSocket.OPEN) ws.send(data)
  })

  resizeObserver = new ResizeObserver(() => {
    if (fitAddon) {
      fitAddon.fit()
      if (ws && ws.readyState === WebSocket.OPEN) {
        const dims = fitAddon.proposeDimensions()
        if (dims) ws.send(`\x1b[RESIZE:${dims.cols},${dims.rows}]`)
      }
    }
  })
  resizeObserver.observe(terminalRef.value!)
}

function connectTerminalWs() {
  if (!sshInfo.host && !sshInfo.consoleMode) { showError('缺少连接信息'); return }

  if (sshInfo.consoleMode) {
    // Console SSH mode (OCI serial console)
    ws = new WebSocket(getConsoleWsUrl())
    ws.onopen = () => {
      connected.value = true
      ws!.send(JSON.stringify({
        ssh_connection_string: sshInfo.sshConnectionString,
        private_key: sshInfo.consolePrivateKey,
      }))
    }
  } else {
    // Normal SSH mode
    ws = new WebSocket(getWsUrl())
    ws.onopen = () => {
      connected.value = true
      ws!.send(JSON.stringify({ type: 'auth', auth_type: sshInfo.authType, password: sshInfo.password || '', private_key: sshInfo.privateKey || '' }))
    }
  }

  ws.onmessage = (event) => terminal?.write(event.data)
  ws.onclose = () => { connected.value = false; terminal?.write('\r\n\x1b[33m连接已断开\x1b[0m\r\n') }
  ws.onerror = () => { connected.value = false; terminal?.write('\r\n\x1b[31mWebSocket 连接错误\x1b[0m\r\n') }
}

// ─── Monitor WebSocket ───────────────────────────────────────────────────────
function connectMonitorWs() {
  if (!sshInfo.host) return
  monitorWs = new WebSocket(getMonitorWsUrl())
  monitorWs.onopen = () => {
    monitorWs!.send(JSON.stringify({ auth_type: sshInfo.authType, password: sshInfo.password || '', private_key: sshInfo.privateKey || '' }))
  }
  monitorWs.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      if (data.error) return
      updateNetHistory(data.network || [])
      if (data.ping_ms !== undefined) updatePingHistory(data.ping_ms)
      Object.assign(sysInfo, data)
    } catch { /* ignore */ }
  }
  monitorWs.onclose = () => { /* silent */ }
  monitorWs.onerror = () => { /* silent */ }
}

// ─── File Manager ────────────────────────────────────────────────────────────
function getSftpPayload(path?: string) {
  return {
    host: sshInfo.host,
    port: sshInfo.port,
    username: sshInfo.username,
    auth_type: sshInfo.authType,
    password: sshInfo.authType === 'password' ? sshInfo.password : '',
    private_key: sshInfo.authType === 'key' ? sshInfo.privateKey : '',
    path: path || currentPath.value,
  }
}

async function loadFiles(path?: string) {
  fileLoading.value = true
  activeFileMenu.value = null
  try {
    const targetPath = path || currentPath.value
    const res = await api.post('/terminal-monitor/files/list', getSftpPayload(targetPath))
    fileList.value = res.data.files
    currentPath.value = res.data.path
    // Update tree: add dirs from this path as children
    updateTree(res.data.path, res.data.files.filter((f: any) => f.is_dir))
  } catch (e: any) {
    showError(e.response?.data?.detail || '加载文件列表失败')
  } finally {
    fileLoading.value = false
  }
}

function updateTree(path: string, dirs: any[]) {
  if (path === '/') {
    // Root level — set top-level tree nodes
    treeNodes.value = dirs.map(d => ({
      name: d.name,
      path: '/' + d.name,
      expanded: false,
      children: [],
    }))
    return
  }
  // Find the node in tree and set its children
  function findAndUpdate(nodes: TreeNode[]): boolean {
    for (const node of nodes) {
      if (node.path === path) {
        node.children = dirs.map(d => ({
          name: d.name,
          path: path + '/' + d.name,
          expanded: false,
          children: [],
        }))
        node.expanded = true
        return true
      }
      if (findAndUpdate(node.children)) return true
    }
    return false
  }
  if (!findAndUpdate(treeNodes.value)) {
    // Path not in tree yet, just load it
  }
}

function onTreeNodeClick(node: TreeNode) {
  if (node.expanded) {
    // 已展开则折叠
    node.expanded = false
  } else {
    // 未展开则加载并展开
    currentPath.value = node.path
    loadFiles(node.path)
  }
}

function enterDir(name: string) {
  const newPath = currentPath.value === '/' ? `/${name}` : `${currentPath.value}/${name}`
  loadFiles(newPath)
}

function goParent() {
  if (currentPath.value === '/') return
  const parts = currentPath.value.split('/')
  parts.pop()
  const parent = parts.join('/') || '/'
  loadFiles(parent)
}

function refreshFiles() {
  loadFiles(currentPath.value)
}

async function doMkdir() {
  const name = prompt('新建文件夹名称:')
  if (!name) return
  const path = currentPath.value === '/' ? `/${name}` : `${currentPath.value}/${name}`
  try {
    await api.post('/terminal-monitor/files/mkdir', { ...getSftpPayload(), path })
    success('文件夹创建成功')
    refreshFiles()
  } catch (e: any) {
    showError(e.response?.data?.detail || '创建失败')
  }
}

async function doDelete(file: any) {
  activeFileMenu.value = null
  const ok = confirm(`⚠️ 确认删除「${file.name}」？此操作不可逆（rm -rf）！`)
  if (!ok) return
  const path = currentPath.value === '/' ? `/${file.name}` : `${currentPath.value}/${file.name}`
  try {
    await api.post('/terminal-monitor/files/delete', { ...getSftpPayload(), path })
    success('删除成功')
    refreshFiles()
  } catch (e: any) {
    showError(e.response?.data?.detail || '删除失败')
  }
}

async function doDownload(file: any) {
  const path = currentPath.value === '/' ? `/${file.name}` : `${currentPath.value}/${file.name}`
  try {
    const res = await api.post('/terminal-monitor/files/download', { ...getSftpPayload(), path }, { responseType: 'blob' })
    const url = URL.createObjectURL(res.data)
    const a = document.createElement('a')
    a.href = url
    a.download = file.name
    a.click()
    URL.revokeObjectURL(url)
  } catch (e: any) {
    showError('下载失败')
  }
}

// ─── Lifecycle ───────────────────────────────────────────────────────────────
onMounted(() => {
  if (!sshInfo.host && !sshInfo.consoleMode) { showError('缺少连接信息'); return }
  initTerminal()
  connectTerminalWs()
  if (!sshInfo.consoleMode) {
    connectMonitorWs()
    loadFiles('/')
  }
  loadQuickCommands()
  document.addEventListener('click', onFileMenuOutsideClick)
})

onUnmounted(() => {
  ws?.close(); ws = null
  monitorWs?.close(); monitorWs = null
  resizeObserver?.disconnect()
  terminal?.dispose()
  document.removeEventListener('click', onFileMenuOutsideClick)
})
</script>
