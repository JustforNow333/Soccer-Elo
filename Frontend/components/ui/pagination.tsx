import * as React from "react"
import Link from "next/link"

export function Pagination({ children, ...props }: React.HTMLAttributes<HTMLNavElement>) {
  return <nav role="navigation" aria-label="pagination" {...props}>{children}</nav>
}

export function PaginationContent({ children, ...props }: React.HTMLAttributes<HTMLUListElement>) {
  return <ul className="flex items-center gap-1" {...props}>{children}</ul>
}

export function PaginationItem({ children, ...props }: React.LiHTMLAttributes<HTMLLIElement>) {
  return <li {...props}>{children}</li>
}

export function PaginationLink({ children, isActive, ...props }: React.AnchorHTMLAttributes<HTMLAnchorElement> & { isActive?: boolean }) {
  return (
    <a
      aria-current={isActive ? "page" : undefined}
      className={`flex h-9 w-9 items-center justify-center rounded-md border border-input bg-background px-0 py-0 text-sm font-medium transition-colors hover:bg-accent hover:text-accent-foreground focus:z-20 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 ${isActive ? "bg-accent text-accent-foreground" : ""}`}
      {...props}
    >
      {children}
    </a>
  )
}

export function PaginationPrevious(props: React.AnchorHTMLAttributes<HTMLAnchorElement>) {
  return <PaginationLink aria-label="Go to previous page" {...props} />
}

export function PaginationNext(props: React.AnchorHTMLAttributes<HTMLAnchorElement>) {
  return <PaginationLink aria-label="Go to next page" {...props} />
}

export function PaginationEllipsis() {
  return <span className="px-2">…</span>
} 