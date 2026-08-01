export default function CalculatorPage() {
  return (
    <div style={{ width: '100%', height: 'calc(100vh - 120px)' }}>
      <h1 className="text-[22px] font-semibold text-[var(--color-charcoal)] mb-4 px-6 pt-4">计算器</h1>
      <iframe
        src="/calculator.html"
        style={{ width: '100%', height: '100%', border: 'none' }}
        title="液相计算表"
      />
    </div>
  )
}
