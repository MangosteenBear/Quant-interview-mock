/**
 * Markdown + LaTeX 渲染器
 * 用 markdown-it 解析 Markdown，@traptitech/markdown-it-katex 渲染 LaTeX 公式
 * 支持 $...$ 行内公式、$$...$$ 行间公式、表格、列表、加粗等
 */
import MarkdownIt from 'markdown-it'
import katexPlugin from '@traptitech/markdown-it-katex'

// 单例 md 实例（避免重复初始化）
const md = new MarkdownIt({
  html: false,       // 安全：题干来自后端，禁原始 html
  linkify: true,     // 自动识别链接
  typographer: true,  // 排版优化
  breaks: true,      // 单换行转 <br>，贴合题干排版
})

// 挂载 KaTeX 插件
md.use(katexPlugin, {
  throwOnError: false,
  errorColor: '#cc0000',
})

/**
 * 将 Markdown 文本渲染为 HTML
 * @param src Markdown 源文本（含 LaTeX 公式）
 * @returns 渲染后的 HTML 字符串
 */
export function renderMarkdown(src: string): string {
  return md.render(src || '')
}
