import React from 'react'
import type { Command } from '@commands'
import { Doctor } from '@screens/Doctor'
import { PRODUCT_NAME } from '@constants/product'

const doctor: Command = {
  name: 'doctor',
  description: `Checks the health of your ${PRODUCT_NAME} installation`,
  isEnabled: true,
  isHidden: false,
  userFacingName() {
    return 'doctor'
  },
  type: 'local-jsx',
  call(onDone) {
    const element = React.createElement(Doctor, {
      onDone,
      doctorMode: true,
    })
    return Promise.resolve(element)
  },
}

export default doctor
