declare module 'js-yaml' {
  const yaml: {
    load(input: string, options?: any): any
    dump(input: any, options?: any): string
  }
  export default yaml
}
