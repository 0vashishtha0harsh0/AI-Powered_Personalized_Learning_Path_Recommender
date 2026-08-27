export default function SectionTitle({
  title, text
}: { title: string; text?: string }) {
  return (
    <div className="section-title">
      <div>
        <h2>{title}</h2>
        {text && <p>{text}</p>}
      </div>
    </div>
  );
}
