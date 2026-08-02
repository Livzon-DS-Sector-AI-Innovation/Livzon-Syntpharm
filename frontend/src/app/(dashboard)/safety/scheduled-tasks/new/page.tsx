import { ScheduledTaskForm } from '@/components/safety'

export default function NewScheduledTaskPage() {
  return (
    <div style={{ padding: '0 0 24px' }}>
      <h1 style={{ marginBottom: 16 }}>新建定时任务</h1>
      <ScheduledTaskForm />
    </div>
  )
}
