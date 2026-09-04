export const dynamic = 'force-dynamic'

import { fetchTrainingSelectTasks } from '@/lib/api/server/hr'
import TrainingSelectTasksClient from '@/components/hr/TrainingSelectTasksClient'

interface TaskItem {
  token: string
  department: string
  training_date: string
  subject: string
  factory: string
  location: string
  trainer: string
  training_method: string
  has_result: boolean
  selected_count: number
  created_at: string
}

export default async function TrainingSelectTasksPage() {
  let tasks: TaskItem[] = []
  try {
    const res = await fetchTrainingSelectTasks()
    tasks = res.data || []
  } catch {
    // Ignore errors, use empty array
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h1 className="text-[22px] font-semibold text-[var(--color-charcoal)]">
          培训选择任务
        </h1>
      </div>
      <TrainingSelectTasksClient initialTasks={tasks} />
    </div>
  )
}
