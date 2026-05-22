<template>
  <div class="space-y-6">
    <h2 class="text-2xl font-bold text-surface-900 dark:text-white">个人设置</h2>

    <div class="grid grid-cols-2 gap-6">
      <!-- Default Private Key -->
      <div class="card p-6 space-y-4">
        <div class="flex items-center gap-3">
          <div class="w-8 h-8 rounded-lg bg-primary-100 dark:bg-primary-900/30 flex items-center justify-center">
            <svg class="w-4 h-4 text-primary-600 dark:text-primary-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
            </svg>
          </div>
          <h3 class="font-semibold text-surface-900 dark:text-white">默认 OCI 私钥</h3>
          <span :class="hasKey ? 'badge-success' : 'badge-neutral'">{{ hasKey ? '已设置' : '未设置' }}</span>
        </div>

        <p class="text-sm text-surface-500 dark:text-surface-400">设置后，添加云账户时私钥栏会自动预填，无需每次粘贴。</p>

        <div v-if="hasKey && !editing" class="flex items-center gap-2 p-3 bg-surface-50 dark:bg-surface-900 rounded-lg font-mono text-sm text-surface-700 dark:text-surface-300">
          <svg class="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" /></svg>
          <span class="break-all">{{ preview }}</span>
          <span class="text-surface-400 ml-1">（已加密存储）</span>
        </div>

        <div v-if="editing || !hasKey">
          <textarea v-model="privateKey" class="input min-h-[160px] font-mono text-xs resize-y" placeholder="-----BEGIN PRIVATE KEY-----&#10;MIIEvw...&#10;-----END PRIVATE KEY-----"></textarea>
          <div class="mt-2">
            <label class="btn-ghost btn-sm cursor-pointer inline-flex">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" /></svg>
              上传私钥文件
              <input type="file" class="hidden" accept=".pem,.key,.txt" @change="handleKeyFileUpload" />
            </label>
          </div>
        </div>

        <div class="flex items-center gap-2">
          <button v-if="!editing && hasKey" class="btn-primary btn-sm" @click="editing = true">修改私钥</button>
          <button v-if="editing || !hasKey" class="btn-primary btn-sm" :disabled="saving" @click="saveKey">保存</button>
          <button v-if="editing" class="btn-secondary btn-sm" @click="cancelEdit">取消</button>
          <button v-if="hasKey" class="btn-danger btn-sm" @click="clearKey">清除私钥</button>
        </div>
      </div>

      <!-- Default SSH Public Key -->
      <div class="card p-6 space-y-4">
        <div class="flex items-center gap-3">
          <div class="w-8 h-8 rounded-lg bg-emerald-100 dark:bg-emerald-900/30 flex items-center justify-center">
            <svg class="w-4 h-4 text-emerald-600 dark:text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
            </svg>
          </div>
          <h3 class="font-semibold text-surface-900 dark:text-white">默认 SSH 公钥</h3>
          <span :class="hasSSHKey ? 'badge-success' : 'badge-neutral'">{{ hasSSHKey ? '已设置' : '未设置' }}</span>
        </div>

        <p class="text-sm text-surface-500 dark:text-surface-400">设置后，新建抢机任务时 SSH 公钥会自动使用此默认值。</p>

        <div v-if="hasSSHKey && !sshEditing" class="flex items-center gap-2 p-3 bg-surface-50 dark:bg-surface-900 rounded-lg font-mono text-sm text-surface-700 dark:text-surface-300">
          <svg class="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" /></svg>
          <span class="break-all">{{ sshPreview }}</span>
        </div>

        <div v-if="sshEditing || !hasSSHKey">
          <textarea v-model="sshPublicKey" class="input min-h-[160px] font-mono text-xs resize-y" placeholder="ssh-rsa AAAAB3NzaC1yc2EAAAA..."></textarea>
          <div class="mt-2">
            <label class="btn-ghost btn-sm cursor-pointer inline-flex">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" /></svg>
              上传公钥文件
              <input type="file" class="hidden" accept=".pub,.txt" @change="handleSSHFileUpload" />
            </label>
          </div>
        </div>

        <div class="flex items-center gap-2">
          <button v-if="!sshEditing && hasSSHKey" class="btn-primary btn-sm" @click="sshEditing = true">修改公钥</button>
          <button v-if="sshEditing || !hasSSHKey" class="btn-primary btn-sm" :disabled="sshSaving" @click="saveSSHKey">保存</button>
          <button v-if="sshEditing" class="btn-secondary btn-sm" @click="cancelSSHEdit">取消</button>
          <button v-if="hasSSHKey" class="btn-danger btn-sm" @click="clearSSHKey">清除公钥</button>
        </div>
      </div>
    </div>

    <!-- Change Password -->
    <div class="card p-6 max-w-lg space-y-4">
      <div class="flex items-center gap-3">
        <div class="w-8 h-8 rounded-lg bg-amber-100 dark:bg-amber-900/30 flex items-center justify-center">
          <svg class="w-4 h-4 text-amber-600 dark:text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
          </svg>
        </div>
        <h3 class="font-semibold text-surface-900 dark:text-white">修改密码</h3>
      </div>

      <form class="space-y-3" @submit.prevent="changePassword">
        <div>
          <label class="label">旧密码</label>
          <input v-model="pwdForm.old_password" type="password" class="input" required />
        </div>
        <div>
          <label class="label">新密码</label>
          <input v-model="pwdForm.new_password" type="password" class="input" required minlength="6" />
        </div>
        <div>
          <label class="label">确认密码</label>
          <input v-model="pwdForm.confirm_password" type="password" class="input" required />
        </div>
        <button type="submit" class="btn-primary" :disabled="pwdSaving">修改密码</button>
      </form>
    </div>

    <!-- SSH Credentials Management -->
    <div class="card p-6 space-y-4">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-3">
          <div class="w-8 h-8 rounded-lg bg-indigo-100 dark:bg-indigo-900/30 flex items-center justify-center">
            <svg class="w-4 h-4 text-indigo-600 dark:text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
          </div>
          <h3 class="font-semibold text-surface-900 dark:text-white">SSH 凭据管理</h3>
        </div>
        <button class="btn-primary btn-sm" @click="openCredAdd">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/></svg>
          添加凭据
        </button>
      </div>

      <p class="text-sm text-surface-500 dark:text-surface-400">管理 SSH 连接时保存的凭据，可在实例管理中快速选择使用。</p>

      <div v-if="sshCreds.length === 0" class="text-center text-surface-400 py-6">暂无已保存的凭据</div>

      <div v-else class="table-container">
        <table class="table">
          <thead>
            <tr>
              <th>标签</th>
              <th>主机</th>
              <th>端口</th>
              <th>用户名</th>
              <th>认证方式</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="cred in sshCreds" :key="cred.id">
              <td class="font-medium">{{ cred.label }}</td>
              <td class="font-mono text-xs">{{ cred.host }}</td>
              <td>{{ cred.port }}</td>
              <td>{{ cred.username }}</td>
              <td>
                <span :class="cred.auth_type === 'key' ? 'badge-info' : 'badge-neutral'">
                  {{ cred.auth_type === 'key' ? '私钥' : '密码' }}
                </span>
              </td>
              <td>
                <div class="flex items-center gap-1">
                  <button class="btn-ghost btn-sm" @click="openCredEdit(cred)">编辑</button>
                  <button class="btn-ghost btn-sm text-red-600 dark:text-red-400" @click="deleteCred(cred)">删除</button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- SSH Credential Add/Edit Modal -->
    <Modal :visible="credDialogVisible" :title="credEditId ? '编辑凭据' : '添加凭据'" width="480px" @close="credDialogVisible = false">
      <div class="space-y-4">
        <div>
          <label class="label">标签</label>
          <input v-model="credForm.label" class="input" placeholder="如：我的VPS" />
        </div>
        <div>
          <label class="label">主机</label>
          <input v-model="credForm.host" class="input" placeholder="IP 或域名" />
        </div>
        <div>
          <label class="label">端口</label>
          <input v-model.number="credForm.port" type="number" class="input" min="1" max="65535" />
        </div>
        <div>
          <label class="label">用户名</label>
          <input v-model="credForm.username" class="input" placeholder="root" />
        </div>
        <div>
          <label class="label">认证方式</label>
          <div class="flex gap-4">
            <label class="flex items-center gap-2 cursor-pointer">
              <input type="radio" v-model="credForm.auth_type" value="password" class="accent-primary-600" /> 密码
            </label>
            <label class="flex items-center gap-2 cursor-pointer">
              <input type="radio" v-model="credForm.auth_type" value="key" class="accent-primary-600" /> 私钥
            </label>
          </div>
        </div>
        <div v-if="credForm.auth_type === 'password'">
          <label class="label">密码</label>
          <input v-model="credForm.password" type="password" class="input" :placeholder="credEditId ? '留空则不修改' : '输入密码'" />
        </div>
        <div v-if="credForm.auth_type === 'key'">
          <label class="label">私钥</label>
          <textarea v-model="credForm.private_key" class="input" rows="5" :placeholder="credEditId ? '留空则不修改' : '粘贴 SSH 私钥内容'"></textarea>
        </div>
      </div>
      <template #footer>
        <button class="btn-secondary" @click="credDialogVisible = false">取消</button>
        <button class="btn-primary" :disabled="credSaving" @click="saveCred">
          {{ credSaving ? '保存中...' : '保存' }}
        </button>
      </template>
    </Modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useToast } from '@/composables/useToast'
import { useModal } from '@/composables/useModal'
import Modal from '@/components/Modal.vue'
import api from '@/api'

const { success, warning, error } = useToast()
const { confirm } = useModal()

const hasKey = ref(false)
const preview = ref('')
const privateKey = ref('')
const editing = ref(false)
const saving = ref(false)

const hasSSHKey = ref(false)
const sshPreview = ref('')
const sshPublicKey = ref('')
const sshEditing = ref(false)
const sshSaving = ref(false)

const pwdSaving = ref(false)
const pwdForm = reactive({ old_password: '', new_password: '', confirm_password: '' })

async function loadKeyStatus() {
  const res = await api.get('/users/me/default-key')
  hasKey.value = res.data.has_key
  preview.value = res.data.preview || ''
}

async function saveKey() {
  if (!privateKey.value.trim()) { warning('请输入私钥内容'); return }
  saving.value = true
  try {
    await api.put('/users/me/default-key', { private_key: privateKey.value })
    success('默认私钥已保存')
    editing.value = false
    privateKey.value = ''
    await loadKeyStatus()
  } finally { saving.value = false }
}

async function clearKey() {
  const ok = await confirm('确认清除默认私钥？', '警告', { type: 'warning' })
  if (!ok) return
  await api.put('/users/me/default-key', { private_key: '' })
  success('已清除')
  hasKey.value = false
  preview.value = ''
  privateKey.value = ''
}

function cancelEdit() { editing.value = false; privateKey.value = '' }

function handleKeyFileUpload(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  const reader = new FileReader()
  reader.onload = (ev) => {
    const content = (ev.target?.result as string)?.trim()
    if (content) { privateKey.value = content; success('已读取私钥文件内容') }
    else { error('文件内容为空') }
  }
  reader.readAsText(file)
}

async function loadSSHKeyStatus() {
  const res = await api.get('/users/me/default-ssh-key')
  hasSSHKey.value = res.data.has_key
  sshPreview.value = res.data.preview || ''
}

async function saveSSHKey() {
  if (!sshPublicKey.value.trim()) { warning('请输入 SSH 公钥内容'); return }
  sshSaving.value = true
  try {
    await api.put('/users/me/default-ssh-key', { ssh_public_key: sshPublicKey.value })
    success('默认 SSH 公钥已保存')
    sshEditing.value = false
    sshPublicKey.value = ''
    await loadSSHKeyStatus()
  } finally { sshSaving.value = false }
}

async function clearSSHKey() {
  const ok = await confirm('确认清除默认 SSH 公钥？', '警告', { type: 'warning' })
  if (!ok) return
  await api.put('/users/me/default-ssh-key', { ssh_public_key: '' })
  success('已清除')
  hasSSHKey.value = false
  sshPreview.value = ''
  sshPublicKey.value = ''
}

function cancelSSHEdit() { sshEditing.value = false; sshPublicKey.value = '' }

function handleSSHFileUpload(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  const reader = new FileReader()
  reader.onload = (ev) => {
    const content = (ev.target?.result as string)?.trim()
    if (content) { sshPublicKey.value = content; success('已读取公钥文件内容') }
    else { error('文件内容为空') }
  }
  reader.readAsText(file)
}

async function changePassword() {
  if (pwdForm.new_password !== pwdForm.confirm_password) { error('两次密码不一致'); return }
  pwdSaving.value = true
  try {
    await api.post('/auth/change-password', { old_password: pwdForm.old_password, new_password: pwdForm.new_password })
    success('密码修改成功，请重新登录')
    Object.assign(pwdForm, { old_password: '', new_password: '', confirm_password: '' })
  } finally { pwdSaving.value = false }
}

// ── SSH Credentials Management ───────────────────────────────────────────────
const sshCreds = ref<any[]>([])
const credDialogVisible = ref(false)
const credEditId = ref<number | null>(null)
const credSaving = ref(false)
const credForm = reactive({
  label: '',
  host: '',
  port: 22,
  username: 'root',
  auth_type: 'password',
  password: '',
  private_key: '',
})

async function loadSSHCreds() {
  try {
    const res = await api.get('/ssh-credentials')
    sshCreds.value = res.data
  } catch { /* ignore */ }
}

function openCredAdd() {
  credEditId.value = null
  Object.assign(credForm, { label: '', host: '', port: 22, username: 'root', auth_type: 'password', password: '', private_key: '' })
  credDialogVisible.value = true
}

async function openCredEdit(cred: any) {
  credEditId.value = cred.id
  // Load secret to pre-fill
  try {
    const res = await api.get(`/ssh-credentials/${cred.id}/secret`)
    Object.assign(credForm, {
      label: cred.label,
      host: res.data.host,
      port: res.data.port,
      username: res.data.username,
      auth_type: res.data.auth_type,
      password: res.data.password || '',
      private_key: res.data.private_key || '',
    })
  } catch {
    Object.assign(credForm, { label: cred.label, host: cred.host, port: cred.port, username: cred.username, auth_type: cred.auth_type, password: '', private_key: '' })
  }
  credDialogVisible.value = true
}

async function saveCred() {
  if (!credForm.label.trim()) { warning('请输入标签'); return }
  if (!credForm.host.trim()) { warning('请输入主机地址'); return }
  if (!credForm.username.trim()) { warning('请输入用户名'); return }

  credSaving.value = true
  try {
    if (credEditId.value) {
      const payload: any = { label: credForm.label, host: credForm.host, port: credForm.port, username: credForm.username, auth_type: credForm.auth_type }
      if (credForm.auth_type === 'password' && credForm.password) payload.password = credForm.password
      if (credForm.auth_type === 'key' && credForm.private_key) payload.private_key = credForm.private_key
      await api.put(`/ssh-credentials/${credEditId.value}`, payload)
      success('凭据已更新')
    } else {
      if (credForm.auth_type === 'password' && !credForm.password) { warning('请输入密码'); credSaving.value = false; return }
      if (credForm.auth_type === 'key' && !credForm.private_key) { warning('请输入私钥'); credSaving.value = false; return }
      await api.post('/ssh-credentials', credForm)
      success('凭据已添加')
    }
    credDialogVisible.value = false
    loadSSHCreds()
  } finally { credSaving.value = false }
}

async function deleteCred(cred: any) {
  const ok = await confirm(`确认删除凭据「${cred.label}」？`, '警告', { type: 'warning' })
  if (!ok) return
  await api.delete(`/ssh-credentials/${cred.id}`)
  success('删除成功')
  loadSSHCreds()
}

onMounted(() => { loadKeyStatus(); loadSSHKeyStatus(); loadSSHCreds() })
</script>
