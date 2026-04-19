export type FormData = {
  name: string
  email: string
  address1: string
  address2: string
  city: string
  state: string
  zip: string
  phone: string
  usLocation: boolean
}

export type ValidationError = {
  message: string
}

export function validateField(
  field: keyof FormData,
  value: string,
): ValidationError | null {
  const trimmed = value.trim()

  if (!trimmed && field === 'address2') {
    return null
  }

  if (!trimmed) {
    return { message: 'This field is required' }
  }

  switch (field) {
    case 'email': {
      const emailRegex =
        /^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$/
      if (!emailRegex.test(trimmed)) {
        return { message: 'Please enter a valid email address' }
      }
      break
    }

    case 'name':
      if (trimmed.length < 2) {
        return { message: 'Name must be at least 2 characters long' }
      }
      break

    case 'address1': {
      if (trimmed.length < 3) {
        return { message: 'Please enter a valid address' }
      }
      const isPOBox = /^P\.?O\.?\s*Box\s+\d+$/i.test(trimmed)
      const hasNumber = /\d+/.test(trimmed)
      if (!isPOBox && !hasNumber) {
        return { message: 'Please include a number in the street address' }
      }
      break
    }
    case 'address2':
      break

    case 'city':
      if (trimmed.length < 2) {
        return { message: 'City name must be at least 2 characters long' }
      }
      if (!/^[a-zA-Z\s.-]+$/.test(trimmed)) {
        return {
          message:
            'City can only contain letters, spaces, periods, and hyphens',
        }
      }
      break

    case 'state': {
      const states = new Set([
        'AL',
        'AK',
        'AZ',
        'AR',
        'CA',
        'CO',
        'CT',
        'DE',
        'FL',
        'GA',
        'HI',
        'ID',
        'IL',
        'IN',
        'IA',
        'KS',
        'KY',
        'LA',
        'ME',
        'MD',
        'MA',
        'MI',
        'MN',
        'MS',
        'MO',
        'MT',
        'NE',
        'NV',
        'NH',
        'NJ',
        'NM',
        'NY',
        'NC',
        'ND',
        'OH',
        'OK',
        'OR',
        'PA',
        'RI',
        'SC',
        'SD',
        'TN',
        'TX',
        'UT',
        'VT',
        'VA',
        'WA',
        'WV',
        'WI',
        'WY',
        'DC',
      ])
      const stateCode = trimmed.toUpperCase()
      if (!states.has(stateCode)) {
        return { message: 'Please enter a valid US state code (e.g. CA)' }
      }
      break
    }

    case 'usLocation': {
      const normalized = trimmed.toLowerCase()
      if (!['y', 'yes', 'n', 'no'].includes(normalized)) {
        return { message: 'Please enter y/yes or n/no' }
      }
      break
    }

    case 'zip':
      if (!/^\d{5}(-\d{4})?$/.test(trimmed)) {
        return {
          message: 'Please enter a valid ZIP code (e.g. 12345 or 12345-6789)',
        }
      }
      break

    case 'phone':
      if (!/^(\+1\s?)?(\d{3}[-.\s]??)?\d{3}[-.\s]??\d{4}$/.test(trimmed)) {
        return {
          message: 'Please enter a valid US phone number',
        }
      }
      break
  }

  return null
}
