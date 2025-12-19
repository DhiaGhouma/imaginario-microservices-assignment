import SearchJobCard from './SearchJobCard';

interface SearchJob {
    job_id: string;
    query: string;
    status: string;
    execution_time?: number;
    created_at: string;
    completed_at?: string;
}

interface SearchJobsListProps {
    jobs: SearchJob[];
    loading: boolean;
}

export default function SearchJobsList({ jobs, loading }: SearchJobsListProps) {
    if (loading) {
        return (
            <div style={{ textAlign: 'center', padding: '40px', color: '#999' }}>
                Loading jobs...
            </div>
        );
    }

    if (!jobs || jobs.length === 0) {
        return (
            <div style={{ textAlign: 'center', padding: '40px' }}>
                <p style={{ color: '#999', fontSize: '15px' }}>
                    No search jobs yet. Start by creating a search!
                </p>
            </div>
        );
    }

    return (
        <div>
            {jobs.map(job => (
                <SearchJobCard key={job.job_id} job={job} />
            ))}
        </div>
    );
}