 
#!/bin/sh


accelerate launch --multi_gpu --num_processes=2 --gpu_ids 6,7 run.py --config_path /scratch/max/mlgym/example/cnn_ddp/run_config.yml
