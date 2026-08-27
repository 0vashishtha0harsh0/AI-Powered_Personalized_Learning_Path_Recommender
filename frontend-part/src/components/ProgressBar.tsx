export default function ProgressBar({
  value,
  className = ""
}: { value: number; className?: string }) {
  return (
    <div className={`progress ${className}`}>
      <span style={{ width: `${value}%` }} />
    </div>
  );
}
