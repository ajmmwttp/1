import { DashboardSkeleton } from "@/components/states/dashboard-skeleton";
import { Skeleton } from "@/components/ui/skeleton";

export default function Loading() {
  return (
    <>
      <header className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <Skeleton className="h-2.5 w-28" />
          <Skeleton className="mt-2.5 h-5 w-64" />
          <Skeleton className="mt-2.5 h-2.5 w-[38ch] max-w-full" />
        </div>
        <div className="flex items-center gap-2">
          <Skeleton className="h-8 w-52 rounded-[8px]" />
          <Skeleton className="h-8 w-28 rounded-[8px]" />
        </div>
      </header>
      <DashboardSkeleton />
    </>
  );
}
