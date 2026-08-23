import { ButtonHTMLAttributes, forwardRef } from "react";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost";
  size?: "sm" | "md";
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ variant = "primary", size = "md", className = "", children, ...props }, ref) => {
    const base =
      "inline-flex items-center justify-center gap-2 rounded-lg font-medium transition-all duration-200 ease-out disabled:opacity-40 disabled:pointer-events-none active:scale-[0.98]";

    const variants = {
      primary:
        "bg-accent text-ink hover:brightness-110 hover:shadow-[0_0_0_1px_var(--color-accent)] shadow-sm",
      secondary:
        "bg-surface-raised text-text border border-border hover:border-border-strong hover:bg-surface",
      ghost:
        "text-text-muted hover:text-text hover:bg-surface",
    };

    const sizes = {
      sm: "px-3 py-1.5 text-sm",
      md: "px-4 py-2 text-sm",
    };

    return (
      <button
        ref={ref}
        className={`${base} ${variants[variant]} ${sizes[size]} ${className}`}
        {...props}
      >
        {children}
      </button>
    );
  }
);
Button.displayName = "Button";