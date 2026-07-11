import { Outlet } from 'react-router-dom';
import { Header } from './Header';
import { Sidebar } from './Sidebar';

export function Layout() {
  return (
    <div className="min-h-screen bg-bgc text-ink">
      <Header />
      <div className="flex items-stretch">
        <Sidebar />
        <main className="flex-1 min-w-0 px-8 pt-[26px] pb-10">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
