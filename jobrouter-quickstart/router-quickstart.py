import time

from azure.communication.jobrouter import (
    JobRouterClient,
    JobRouterAdministrationClient
)

from azure.communication.jobrouter.models import (
    DistributionPolicy,
    LongestIdleMode,
    RouterQueue,
    RouterJob,
    RouterWorkerSelector,
    LabelOperator,
    RouterWorker,
    RouterChannel,
    CloseJobOptions
)

class RouterQuickstart(object):
    print("Azure Communication Services - Job Router Quickstart")
    
    # Get a connection string to our Azure Communication Services resource.
    connection_string = "conn_str"
    router_admin_client = JobRouterAdministrationClient.from_connection_string(conn_str = connection_string)
    router_client = JobRouterClient.from_connection_string(conn_str = connection_string)
    
    distribution_policy = router_admin_client.upsert_distribution_policy(
        "distribution-policy-1",
        DistributionPolicy(
            offer_expires_after_seconds = 60,
            mode = LongestIdleMode(),
            name = "My distribution policy"
        ))
    
    queue = router_admin_client.upsert_queue(
        "queue-1",
        RouterQueue(
            name = "My Queue",
            distribution_policy_id = distribution_policy.id
        ))
    
    job = router_client.upsert_job(
        "job-1",
        RouterJob(
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
    
    worker = router_client.upsert_worker(
        "worker-1",
        RouterWorker(
            capacity = 1,
            queues = [
                "queue-1",
            ],
            labels = {
                "Some-Skill": 11
            },
            channels = [
                RouterChannel(channel_id = "voice", capacity_cost_per_job = 1)
            ],
            available_for_offers = True
        ))
    
    time.sleep(10)
    worker = router_client.get_worker(worker_id = worker.id)
    for offer in worker.offers:
        print(f"Worker {worker.id} has an active offer for job {offer.job_id}")
        
    accept = router_client.accept_job_offer(worker_id = worker.id, offer_id = worker.offers[0].offer_id)
    print(f"Worker {worker.id} is assigned job {accept.job_id}")
    
    router_client.complete_job(job_id = job.id, assignment_id = accept.assignment_id)
    print(f"Worker {worker.id} has completed job {accept.job_id}")
    
    router_client.close_job(job_id = job.id, assignment_id = accept.assignment_id, options = CloseJobOptions(disposition_code = "Resolved"))
    print(f"Worker {worker.id} has closed job {accept.job_id}")

    router_client.delete_job(accept.job_id)
    print(f"Deleting {accept.job_id}")


if __name__ == '__main__':
    router = RouterQuickstart()