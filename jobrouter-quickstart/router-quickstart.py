import time
from azure.communication.jobrouter import (
    JobRouterClient,
    JobRouterAdministrationClient,
    DistributionPolicy,
    LongestIdleMode,
    RouterQueue,
    RouterJob,
    RouterWorkerSelector,
    LabelOperator,
    RouterWorker,
    ChannelConfiguration
)

class RouterQuickstart(object):
    print("Azure Communication Services - Job Router Quickstart")
    
    # Get a connection string to our Azure Communication Services resource.
    connection_string = "your_connection_string"
    router_admin_client = JobRouterAdministrationClient.from_connection_string(conn_str = connection_string)
    router_client = JobRouterClient.from_connection_string(conn_str = connection_string)
    
    distribution_policy = router_admin_client.create_distribution_policy(
    distribution_policy_id ="distribution-policy-1",
    distribution_policy = DistributionPolicy(
        offer_expires_after_seconds = 60,
        mode = LongestIdleMode(),
        name = "My distribution policy"
    ))
    
    queue = router_admin_client.create_queue(
        queue_id = "queue-1",
        queue = RouterQueue(
            name = "My Queue",
            distribution_policy_id = distribution_policy.id
        ))
    
    job = router_client.create_job(
        job_id = "job-1",
        router_job = RouterJob(
            channel_id = "voice",
            queue_id = queue.id,
            priority = 1,
            requested_worker_selectors = [
                RouterWorkerSelector(
                    key = "Some-Skill",
                    label_operator = LabelOperator.GREATER_THAN,
                    value = 10
                )
            ]
        ))
    
    worker = router_client.create_worker(
        worker_id = "worker-1",
        router_worker = RouterWorker(
            total_capacity = 1,
            queue_assignments = {
                queue.id: {}
            },
            labels = {
                "Some-Skill": 11
            },
            channel_configurations = {
                "voice": ChannelConfiguration(capacity_cost_per_job = 1)
            },
            available_for_offers = True
        ))
    
    time.sleep(3)
    worker = router_client.get_worker(worker_id = worker.id)
    for offer in worker.offers:
        print(f"Worker {worker.id} has an active offer for job {offer.job_id}")
        
    accept = router_client.accept_job_offer(worker_id = worker.id, offer_id = worker.offers[0].offer_id)
    print(f"Worker {worker.id} is assigned job {accept.job_id}")
    
    router_client.complete_job(job_id = job.id, assignment_id = accept.assignment_id)
    print(f"Worker {worker.id} has completed job {accept.job_id}")
    
    router_client.close_job(job_id = job.id, assignment_id = accept.assignment_id, disposition_code = "Resolved")
    print(f"Worker {worker.id} has closed job {accept.job_id}")

    router_client.delete_job(accept.job_id)
    print(f"Deleting {accept.job_id}")

if __name__ == '__main__':
    router = RouterQuickstart()
