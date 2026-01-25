import { useTranslation } from 'react-i18next';
import { BarChart3, LogOut, Moon, Settings, Sun, User } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

import { Dropdown } from './Dropdown';
import { ToggleButton } from './ToggleButton';
import { useTheme } from '../context/ThemeContext';
import { useLogoutMutation } from '../hooks/useAuth';
import { useLoginEnabled } from '../hooks/useFeatures';

type ProfileMenuProps = {
    profileName: string;
    profileInitial: string;
    avatarUrl?: string;
};

export function ProfileMenu({ profileName, profileInitial, avatarUrl }: ProfileMenuProps) {
    const { t } = useTranslation();
    const { theme, toggleTheme } = useTheme();
    const navigate = useNavigate();
    const logoutMutation = useLogoutMutation();
    const { loginEnabled } = useLoginEnabled();

    return (
        <Dropdown
            side="right"
            align="start"
            offsetX={4}
            positionClassName="top-1"
            menuClassName="w-48"
            trigger={
                <button
                    type="button"
                    className="flex h-8 w-8 items-center justify-center rounded-full border border-[color:var(--color-border-strong)] bg-[color:var(--color-surface)] font-display text-sm font-semibold text-[color:var(--color-text)] shadow-[0_8px_20px_rgba(15,23,42,0.12)] transition duration-200 hover:-translate-y-0.5 hover:shadow-[0_12px_26px_rgba(15,23,42,0.18)]"
                    aria-label={`${profileName}`}
                    title={profileName}
                >
                    {avatarUrl ? (
                        <img
                            src={avatarUrl}
                            alt=""
                            className="h-full w-full rounded-full object-cover"
                        />
                    ) : (
                        <span aria-hidden="true">{profileInitial}</span>
                    )}
                </button>
            }
        >
            {({ close }) => (
                <>
                    <button
                        type="button"
                        className="menu-item flex w-full items-center justify-between rounded-xl px-3 py-2 text-sm font-semibold"
                        role="menuitem"
                        onClick={() => {
                            close();
                            navigate('/app/settings#profile');
                        }}
                    >
                        <span className="flex items-center gap-3">
                            <User className="h-4 w-4 text-muted" aria-hidden="true" />
                            <span>{t('profileMenu.profile')}</span>
                        </span>
                    </button>
                    <button
                        type="button"
                        className="menu-item flex w-full items-center justify-between rounded-xl px-3 py-2 text-sm font-semibold"
                        role="menuitem"
                        onClick={() => {
                            close();
                            navigate('/app/insights');
                        }}
                    >
                        <span className="flex items-center gap-3">
                            <BarChart3 className="h-4 w-4 text-muted" aria-hidden="true" />
                            <span>{t('profileMenu.knowledgeInsights')}</span>
                        </span>
                    </button>
                    <div
                        className="menu-item flex w-full items-center justify-between rounded-xl px-3 py-2 text-sm font-semibold"
                        role="menuitem"
                        tabIndex={0}
                        onClick={() => toggleTheme()}
                        onKeyDown={(event) => {
                            if (event.key === 'Enter' || event.key === ' ') {
                                event.preventDefault();
                                toggleTheme();
                            }
                        }}
                    >
                        <span className="flex items-center gap-3">
                            {theme === 'dark' ? (
                                <Moon className="h-4 w-4 text-muted" aria-hidden="true" />
                            ) : (
                                <Sun className="h-4 w-4 text-muted" aria-hidden="true" />
                            )}
                            <span>{t('profileMenu.theme')}</span>
                        </span>
                        <ToggleButton
                            checked={theme === 'dark'}
                            onChange={toggleTheme}
                            stopPropagation
                            size="sm"
                        />
                    </div>
                    <button
                        type="button"
                        className="menu-item flex w-full items-center justify-between rounded-xl px-3 py-2 text-sm font-semibold"
                        role="menuitem"
                        onClick={() => {
                            close();
                            navigate('/app/settings#general');
                        }}
                    >
                        <span className="flex items-center gap-3">
                            <Settings className="h-4 w-4 text-muted" aria-hidden="true" />
                            <span>{t('profileMenu.settings')}</span>
                        </span>
                    </button>
                    {loginEnabled ? (
                        <button
                            type="button"
                            className="menu-item flex w-full items-center justify-between rounded-xl px-3 py-2 text-sm font-semibold"
                            role="menuitem"
                            disabled={logoutMutation.isPending}
                            onClick={() => {
                                close();
                                logoutMutation.mutate(undefined, {
                                    onSettled: () => {
                                        navigate('/');
                                    },
                                });
                            }}
                        >
                            <span className="flex items-center gap-3">
                                <LogOut className="h-4 w-4 text-muted" aria-hidden="true" />
                                <span>{t('profileMenu.logout')}</span>
                            </span>
                        </button>
                    ) : null}
                </>
            )}
        </Dropdown>
    );
}
