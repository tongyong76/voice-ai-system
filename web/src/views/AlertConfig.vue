<template>
  <div class="alert-config">
    <el-card shadow="hover">
      <template #header>
        <div class="card-header">
          <span>告警配置</span>
          <el-button type="primary" @click="showCreateDialog = true">
            <el-icon><Plus /></el-icon>
            添加规则
          </el-button>
        </div>
      </template>

      <!-- Alert Rules Table -->
      <el-table :data="rules" style="width: 100%" v-loading="loading">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="name" label="规则名称" width="200" />
        <el-table-column prop="condition_type" label="条件类型" width="120">
          <template #default="{ row }">
            <el-tag>{{ row.condition_type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="action_type" label="动作类型" width="120" />
        <el-table-column prop="action_target" label="动作目标" width="200" />
        <el-table-column prop="enabled" label="状态" width="100">
          <template #default="{ row }">
            <el-switch v-model="row.enabled" @change="toggleRule(row)" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" @click="editRule(row)">编辑</el-button>
            <el-button text type="danger" @click="deleteRule(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- Alert Logs -->
    <el-card shadow="hover" class="mt-16">
      <template #header>
        <div class="card-header">
          <span>告警记录</span>
          <el-button text @click="fetchLogs">刷新</el-button>
        </div>
      </template>

      <el-table :data="logs" style="width: 100%">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="rule_id" label="规则ID" width="100" />
        <el-table-column prop="audio_id" label="音频ID" width="100" />
        <el-table-column prop="triggered_at" label="触发时间" width="180">
          <template #default="{ row }">
            {{ formatTime(row.triggered_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="acknowledged" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.acknowledged ? 'success' : 'warning'">
              {{ row.acknowledged ? '已确认' : '待确认' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button
              v-if="!row.acknowledged"
              text
              type="primary"
              @click="acknowledgeLog(row)"
            >
              确认
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- Create/Edit Dialog -->
    <el-dialog v-model="showCreateDialog" :title="editingRule ? '编辑规则' : '添加规则'" width="600px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="规则名称" required>
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="条件类型" required>
          <el-select v-model="form.condition_type" style="width: 100%">
            <el-option label="关键词" value="keyword" />
            <el-option label="说话人" value="speaker" />
            <el-option label="情感" value="emotion" />
            <el-option label="自定义" value="custom" />
          </el-select>
        </el-form-item>
        <el-form-item label="触发条件" required>
          <el-input
            v-model="form.condition_expr_str"
            type="textarea"
            :rows="3"
            placeholder='{"keyword": "危险"} 或 {"speaker_id": 1}'
          />
        </el-form-item>
        <el-form-item label="动作类型" required>
          <el-select v-model="form.action_type" style="width: 100%">
            <el-option label="WebSocket推送" value="websocket" />
            <el-option label="短信" value="sms" />
            <el-option label="邮件" value="email" />
            <el-option label="Webhook" value="webhook" />
          </el-select>
        </el-form-item>
        <el-form-item label="动作目标" required>
          <el-input v-model="form.action_target" placeholder="手机号/邮箱/URL" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import dayjs from 'dayjs'
import request from '@/api/request'

interface AlertRule {
  id: number
  name: string
  condition_type: string
  condition_expr: Record<string, any>
  action_type: string
  action_target: string
  enabled: boolean
}

interface AlertLog {
  id: number
  rule_id: number
  audio_id: number
  triggered_at: string
  acknowledged: boolean
}

const rules = ref<AlertRule[]>([])
const logs = ref<AlertLog[]>([])
const loading = ref(false)
const showCreateDialog = ref(false)
const editingRule = ref<AlertRule | null>(null)

const form = ref({
  name: '',
  condition_type: 'keyword',
  condition_expr_str: '{}',
  action_type: 'websocket',
  action_target: '',
})

const formatTime = (time: string) => dayjs(time).format('YYYY-MM-DD HH:mm:ss')

const fetchRules = async () => {
  loading.value = true
  try {
    rules.value = await request.get('/alert/rules')
  } catch (error) {
    // Error handled
  } finally {
    loading.value = false
  }
}

const fetchLogs = async () => {
  try {
    logs.value = await request.get('/alert/logs')
  } catch (error) {
    // Error handled
  }
}

const toggleRule = async (rule: AlertRule) => {
  try {
    await request.put(`/alert/rules/${rule.id}`, rule)
    ElMessage.success('更新成功')
  } catch (error) {
    // Error handled
  }
}

const editRule = (rule: AlertRule) => {
  editingRule.value = rule
  form.value = {
    name: rule.name,
    condition_type: rule.condition_type,
    condition_expr_str: JSON.stringify(rule.condition_expr),
    action_type: rule.action_type,
    action_target: rule.action_target,
  }
  showCreateDialog.value = true
}

const deleteRule = async (rule: AlertRule) => {
  await ElMessageBox.confirm('确定删除该规则？', '确认')
  try {
    await request.delete(`/alert/rules/${rule.id}`)
    ElMessage.success('删除成功')
    fetchRules()
  } catch (error) {
    // Error handled
  }
}

const acknowledgeLog = async (log: AlertLog) => {
  try {
    await request.put(`/alert/logs/${log.id}/acknowledge`)
    ElMessage.success('已确认')
    fetchLogs()
  } catch (error) {
    // Error handled
  }
}

const handleSave = async () => {
  try {
    const data = {
      ...form.value,
      condition_expr: JSON.parse(form.value.condition_expr_str),
    }
    if (editingRule.value) {
      await request.put(`/alert/rules/${editingRule.value.id}`, data)
    } else {
      await request.post('/alert/rules', data)
    }
    ElMessage.success('保存成功')
    showCreateDialog.value = false
    editingRule.value = null
    form.value = { name: '', condition_type: 'keyword', condition_expr_str: '{}', action_type: 'websocket', action_target: '' }
    fetchRules()
  } catch (error) {
    ElMessage.error('保存失败，请检查条件格式')
  }
}

onMounted(() => {
  fetchRules()
  fetchLogs()
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.mt-16 {
  margin-top: 16px;
}
</style>
