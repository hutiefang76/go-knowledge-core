// 自定义 Typst 模板 - 表格带边框线

#set page(
  paper: "a4",
  margin: (x: 2cm, y: 2.5cm),
  background: {
    place(
      center + horizon,
      rotate(
        -45deg,
        text(
          size: 42pt,
          fill: rgb(0, 0, 0, 8%),
          font: "PingFang SC",
          tracking: 0.2em,
          "知乎@大大大大大芳 付费课程专用"
        )
      )
    )
  },
  header: align(right, text(size: 8pt, fill: luma(120), "知乎" + "@" + "大大大大大芳 付费课程专用")),
  footer: context align(center)[
    #text(size: 8pt, fill: luma(120))[知乎\@大大大大大芳 付费课程专用 | 第 #counter(page).display() 页]
  ],
)

#set text(
  font: ("PingFang SC", "Noto Sans CJK SC"),
  size: 10.5pt,
  lang: "zh",
)

#show raw: set text(font: ("SF Mono", "Menlo", "Monaco"))

// 代码块样式
#show raw.where(block: true): block.with(
  fill: luma(245),
  inset: 10pt,
  radius: 4pt,
  width: 100%,
)

// 表格样式 - 添加边框线
#show table: set table(
  stroke: 0.5pt + luma(150),
  inset: 8pt,
)

#show table.cell.where(y: 0): set text(weight: "bold")
#show table.cell.where(y: 0): set table.cell(fill: luma(230))

// 标题样式
#show heading.where(level: 1): it => {
  pagebreak(weak: true)
  text(size: 20pt, weight: "bold", it)
  v(0.5em)
}

#show heading.where(level: 2): it => {
  v(1em)
  text(size: 16pt, weight: "bold", it)
  v(0.3em)
}

#show heading.where(level: 3): it => {
  v(0.8em)
  text(size: 13pt, weight: "bold", it)
  v(0.2em)
}

// 引用块样式
#show quote: it => {
  block(
    fill: luma(245),
    inset: (left: 12pt, rest: 10pt),
    stroke: (left: 3pt + rgb("#0066cc")),
    it.body
  )
}

// 链接样式
#show link: set text(fill: rgb("#0066cc"))

// 水平分隔线
#let horizontalrule = line(length: 100%, stroke: 0.5pt + luma(180))

$body$
