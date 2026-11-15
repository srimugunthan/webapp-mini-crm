import { useQueryClient } from "@tanstack/react-query";

/** Every LinkedIn link goes through /go/{id} so visits are recorded (FR-26). Works for middle-click too. */
export default function LinkedInLink({ id, url }: { id: number; url: string }) {
  const qc = useQueryClient();
  const refresh = () => {
    // the click opens a new tab; refetch shortly after so "last visited" updates without a reload (FR-31)
    setTimeout(() => {
      qc.invalidateQueries({ queryKey: ["contacts"] });
      qc.invalidateQueries({ queryKey: ["members"] });
    }, 700);
  };
  return (
    <a href={`/go/${id}`} target="_blank" rel="noopener" onClick={refresh} onAuxClick={refresh} title={url}>
      {url.replace("https://www.linkedin.com/", "")}
    </a>
  );
}
