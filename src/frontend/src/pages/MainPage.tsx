import { KnowledgeSearchCard } from '../components/dashboard/KnowledgeSearchCard';

export function MainPage() {
    return (
        <div className="w-full space-y-10">
            <KnowledgeSearchCard inputId="knowledge-search-primary" />
        </div>
    );
}
