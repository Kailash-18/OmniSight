// Inline SVG art: no network images, so screenshots are identical every run.
const shapes = {
  mug: (ink) => (
    <>
      <rect x="62" y="52" width="66" height="78" rx="10" fill={ink} />
      <path d="M128 70 h12 a16 16 0 0 1 0 32 h-12" fill="none" stroke={ink} strokeWidth="9" />
      <rect x="54" y="132" width="82" height="7" rx="3.5" fill={ink} opacity=".35" />
    </>
  ),
  tote: (ink) => (
    <>
      <path d="M76 66 v-14 a24 24 0 0 1 48 0 v14" fill="none" stroke={ink} strokeWidth="7" />
      <path d="M58 66 h84 l-8 76 h-68 z" fill={ink} />
    </>
  ),
  lamp: (ink) => (
    <>
      <path d="M78 46 h44 l14 34 h-72 z" fill={ink} />
      <rect x="96" y="80" width="8" height="50" fill={ink} />
      <rect x="70" y="130" width="60" height="10" rx="5" fill={ink} />
    </>
  ),
}

export default function ProductArt({ product }) {
  return (
    <svg className="product-art" viewBox="0 0 200 180" role="img" aria-label={product.name} style={{ background: product.tint }}>
      {shapes[product.id](product.ink)}
    </svg>
  )
}
