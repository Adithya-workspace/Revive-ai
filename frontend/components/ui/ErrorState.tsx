import { AlertCircle } from "lucide-react";

export function ErrorState({ message }: { message?: string }) {
  return (
    <div className="py-16 text-center space-y-2">
      <AlertCircle size={28} className="mx-auto text-critical" />
      <p className="text-sm text-text">
        {message || "Something went wrong loading this data."}
      </p>
      <p className="text-xs text-text-faint">
        Check that the backend is running, then refresh the page.
      </p>
    </div>
  );
}