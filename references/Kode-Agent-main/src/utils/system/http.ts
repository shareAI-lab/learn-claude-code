
import { MACRO } from '@constants/macros'
import { PRODUCT_COMMAND } from '@constants/product'

export const USER_AGENT = `${PRODUCT_COMMAND}/${MACRO.VERSION} (${process.env.USER_TYPE})`
