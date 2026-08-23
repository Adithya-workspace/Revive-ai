import { HTMLAttributes } from "react";

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  hoverable?: boolean;
}

export function Card({ hoverable = false, className = "", children, ...props }: CardProps) {
  return (
    <div
      className={`rounded-xl border border-border bg-surface p-5 transition-all duration-200 ease-out ${
        hoverable ? "hover:border-border-strong hover:bg-surface-raised cursor-pointer" : ""
      } ${className}`}
      {...props}
    >
      {children}
    </div>
  );
}