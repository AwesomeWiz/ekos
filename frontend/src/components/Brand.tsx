import logo from '../assets/ekos-logo.png';

export function BrandMark({ className = '' }: { className?: string }) {
  return <span className={`brand-mark ${className}`}><img src={logo} alt="" /></span>;
}
export function Brand() {
  return <span className="brand"><BrandMark /><span>EKOS</span></span>;
}
