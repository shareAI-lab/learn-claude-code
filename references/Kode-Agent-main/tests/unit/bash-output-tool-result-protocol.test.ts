import { expect, test } from 'bun:test'
import { TaskOutputTool } from '@tools/TaskOutputTool/TaskOutputTool'

test('TaskOutputTool resultForAssistant matches Claude tag protocol', () => {
  const out: any = {
    retrieval_status: 'success',
    task: {
      task_id: 'babc123',
      task_type: 'local_bash',
      status: 'completed',
      description: 'echo hi',
      exitCode: 0,
      output: 'hi',
    },
  }

  const rendered = TaskOutputTool.renderResultForAssistant(out)
  expect(rendered).toBe(
    [
      '<retrieval_status>success</retrieval_status>',
      '<task_id>babc123</task_id>',
      '<task_type>local_bash</task_type>',
      '<status>completed</status>',
      '<exit_code>0</exit_code>',
      '<output>\nhi\n</output>',
    ].join('\n\n'),
  )
})
