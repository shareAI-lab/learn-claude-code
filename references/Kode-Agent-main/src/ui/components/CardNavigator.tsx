import React, {
  useState,
  useRef,
  ReactNode,
  createContext,
  useContext,
} from 'react'
import { useInput } from 'ink'

interface NavigationContextType {
  pushCard: (card: CardContent) => void
  popCard: () => boolean
  replaceCard: (card: CardContent) => void
  currentDepth: number
}

const NavigationContext = createContext<NavigationContextType | null>(null)

export function useCardNavigation() {
  const context = useContext(NavigationContext)
  if (!context) {
    throw new Error('useCardNavigation must be used within CardNavigator')
  }
  return context
}

export interface CardContent {
  id: string
  content: ReactNode
}

interface CardNavigatorProps {
  onExit?: () => void
  children: ReactNode
}

export function CardNavigator({ onExit, children }: CardNavigatorProps) {
  const [cardStack, setCardStack] = useState<CardContent[]>([])
  const escapeHandledRef = useRef(false)

  const pushCard = (card: CardContent) => {
    setCardStack(prev => [...prev, card])
  }

  const popCard = (): boolean => {
    if (cardStack.length > 0) {
      setCardStack(prev => prev.slice(0, -1))
      return true
    }
    return false
  }

  const replaceCard = (card: CardContent) => {
    if (cardStack.length > 0) {
      setCardStack(prev => [...prev.slice(0, -1), card])
    } else {
      setCardStack([card])
    }
  }

  useInput(
    (input, key) => {
      if (key.escape && !escapeHandledRef.current) {
        escapeHandledRef.current = true

        setTimeout(() => {
          escapeHandledRef.current = false
        }, 100)

        const popped = popCard()

        if (!popped && onExit) {
          onExit()
        }
      }
    },
    { isActive: true },
  )

  const contextValue: NavigationContextType = {
    pushCard,
    popCard,
    replaceCard,
    currentDepth: cardStack.length,
  }

  const currentCard = cardStack[cardStack.length - 1]

  return (
    <NavigationContext.Provider value={contextValue}>
      {currentCard ? currentCard.content : children}
    </NavigationContext.Provider>
  )
}
