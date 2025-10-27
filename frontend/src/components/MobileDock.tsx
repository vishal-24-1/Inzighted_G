import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Home as HomeIcon, Rocket } from 'lucide-react';

interface MobileDockProps {
    /** Optional override routes */
    homeRoute?: string;
    boostRoute?: string;
    className?: string;
}

const MobileDock: React.FC<MobileDockProps> = ({ homeRoute = '/', boostRoute = '/boost', className = '' }) => {
    const navigate = useNavigate();
    const location = useLocation();

    const pathname = location.pathname.toLowerCase();

    const isActive = (route: string) => {
        const r = route.toLowerCase();
        if (r === '/') return pathname === '/';
        // match exact or prefix so child routes are highlighted
        return pathname === r || pathname.startsWith(r + '/') || pathname.includes(r.replace(/^\//, ''));
    };

    const items = [
        {
            key: 'home',
            label: 'Home',
            icon: <HomeIcon size={16} className="pointer-events-none" />,
            route: homeRoute,
        },
        {
            key: 'boost',
            label: 'Boost',
            icon: <Rocket size={16} className="pointer-events-none" />,
            route: boostRoute,
        },
    ];

    return (
        <nav
            aria-label="Mobile dock"
            className={`fixed bottom-2 left-0 right-0 mx-auto max-w-sm px-2 z-30 mobile-dock ${className}`}
            data-tour="mobile-dock"
        >
            <div className="bg-white border border-gray-200 rounded-2xl shadow-md px-1 py-1 flex items-center justify-between gap-1">
                {items.map((it) => {
                    const active = isActive(it.route);
                    return (
                        <button
                            key={it.key}
                            onClick={() => navigate(it.route)}
                            aria-label={it.label}
                            aria-current={active ? 'page' : undefined}
                            className={`flex-1 flex flex-col items-center justify-center gap-0.5 py-1 px-2 rounded-md transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-blue-200 ${active ? 'text-blue-600' : 'text-gray-700 hover:text-gray-900'}`}
                        >
                            <div className="flex items-center justify-center w-8 h-8">
                                {React.cloneElement(it.icon as any, { size: 18, strokeWidth: 3 })}
                            </div>
                            <span className="text-xs font-medium leading-4">{it.label}</span>
                        </button>
                    );
                })}
            </div>
        </nav>
    );
};

export default MobileDock;
