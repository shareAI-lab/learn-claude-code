import React from 'react'
import type { Message } from './query'

let getMessages: () => Message[] = () => []
let setMessages: React.Dispatch<React.SetStateAction<Message[]>> = () => {}

export function setMessagesGetter(getter: () => Message[]) {
  getMessages = getter
}

export function getMessagesGetter(): () => Message[] {
  return getMessages
}

export function setMessagesSetter(
  setter: React.Dispatch<React.SetStateAction<Message[]>>,
) {
  setMessages = setter
}

export function getMessagesSetter(): React.Dispatch<
  React.SetStateAction<Message[]>
> {
  return setMessages
}

let onModelConfigChange: (() => void) | null = null

export function setModelConfigChangeHandler(handler: () => void) {
  onModelConfigChange = handler
}

export function triggerModelConfigChange() {
  if (onModelConfigChange) {
    onModelConfigChange()
  }
}
