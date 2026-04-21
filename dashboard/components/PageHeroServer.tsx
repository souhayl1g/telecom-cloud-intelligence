import { ReactNode } from 'react';

interface PageHeroValue {
    icon?: ReactNode;
    text: string;
}

interface PageHeroServerProps {
    eyebrow: string;
    title: string;
    description: string;
    values?: PageHeroValue[];
    right?: ReactNode;
    showBrand?: boolean;
}

const CheckIcon = (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
        <polyline points="20 6 9 17 4 12" />
    </svg>
);

export default function PageHeroServer({ eyebrow, title, description, values, right, showBrand = true }: PageHeroServerProps) {
    return (
        <section className="page-hero">
            <div className="page-hero-main">
                <div className="page-hero-eyebrow">
                    <span className="page-hero-eyebrow-dot" />
                    {eyebrow}
                </div>
                <h1 className="page-hero-title">{title}</h1>
                <p className="page-hero-description">{description}</p>
                {values && values.length > 0 && (
                    <div className="page-hero-value">
                        {values.map((v, i) => (
                            <div className="page-hero-value-item" key={i}>
                                {v.icon ?? CheckIcon}
                                <span>{v.text}</span>
                            </div>
                        ))}
                    </div>
                )}
            </div>
            <div className="page-hero-side">
                {showBrand && (
                    <div className="brand-dual" title="Tunisie Telecom operating on Huawei Cloud Stack">
                        <span className="brand-dual-tt">
                            <span className="brand-dual-dot" style={{ background: 'var(--brand-tt)' }} />
                            TT
                        </span>
                        <span className="brand-dual-x">on</span>
                        <span className="brand-dual-huawei">
                            <span className="brand-dual-dot" style={{ background: 'var(--brand-huawei)' }} />
                            Huawei&nbsp;HCS
                        </span>
                    </div>
                )}
                {right}
            </div>
        </section>
    );
}
