import React from 'react'
import { Box, Text } from 'ink'
import type { TodoItem as TodoItemType } from '@utils/session/todoStorage'

export interface TodoItemProps {
  todo: TodoItemType
  children?: React.ReactNode
}

export const TodoItem: React.FC<TodoItemProps> = ({ todo, children }) => {
  const statusIconMap = {
    completed: '✅',
    in_progress: '🔄',
    pending: '⏸️',
  }

  const statusColorMap = {
    completed: '#008000',
    in_progress: '#FFA500',
    pending: '#FFD700',
  }

  const priorityIconMap = {
    high: '🔴',
    medium: '🟡',
    low: '🟢',
  }

  const icon = statusIconMap[todo.status]
  const color = statusColorMap[todo.status]
  const priorityIcon = todo.priority ? priorityIconMap[todo.priority] : ''

  return (
    <Box flexDirection="row" gap={1}>
      <Text color={color}>{icon}</Text>
      {priorityIcon && <Text>{priorityIcon}</Text>}
      <Text
        color={color}
        strikethrough={todo.status === 'completed'}
        bold={todo.status === 'in_progress'}
      >
        {todo.content}
      </Text>
      {children}
    </Box>
  )
}
