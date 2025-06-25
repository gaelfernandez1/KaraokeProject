import torch
import subprocess
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def detect_gpu_capability():

    gpu_info = {
        'has_cuda': False,
        'cuda_available': False,
        'gpu_count': 0,
        'gpu_memory': 0,
        'recommended_device': 'cpu',
        'cuda_version': None,
        'gpu_name': 'Unknown'
    }
    
    try:
        gpu_info['cuda_available'] = torch.cuda.is_available()
        
        if gpu_info['cuda_available']:
            gpu_info['has_cuda'] = True
            gpu_info['gpu_count'] = torch.cuda.device_count()
            
            if gpu_info['gpu_count'] > 0:
                props = torch.cuda.get_device_properties(0)
                gpu_info['gpu_memory'] = props.total_memory / (1024**3)  
                gpu_info['gpu_name'] = props.name
                gpu_info['cuda_version'] = torch.version.cuda
                if gpu_info['gpu_memory'] >= 3.5: 
                    gpu_info['recommended_device'] = 'cuda'
                else:
                    gpu_info['recommended_device'] = 'cpu'  
            
        logger.info(f"resultado: {gpu_info}")
        
    except Exception as e:
        logger.error(f"error con gpu: {e}")
        gpu_info['recommended_device'] = 'cpu'
    
    return gpu_info

def get_optimal_demucs_args(gpu_info):

    base_args = ['--two-stems=vocals']
    
    if gpu_info['recommended_device'] == 'cuda':
        base_args.extend([
            '--device', 'cuda',
            '--shifts', '1',  
            '--overlap', '0.25'
        ])
          
        if gpu_info['gpu_memory'] < 5:
            base_args.extend(['--segment', '5'])  
        elif gpu_info['gpu_memory'] < 6:
            base_args.extend(['--segment', '8'])  
        elif gpu_info['gpu_memory'] >= 8:
            base_args.extend(['--segment', '15'])  
        else:
            base_args.extend(['--segment', '10'])  
            
    else:  #cpu
        
        base_args.extend([
            '--device', 'cpu',
            '--shifts', '1',
            '--jobs', '2',  
            '--segment', '10'
        ])
    
    return base_args

def test_cuda_functionality():

    try:
        if torch.cuda.is_available():
            x = torch.randn(100, 100).cuda()
            y = torch.matmul(x, x)
            del x, y  
            torch.cuda.empty_cache()
            return True
    except Exception as e:
        return False
    
    return False


#un par de funciones para logs


def get_system_info():

    gpu_info = detect_gpu_capability()
    
    system_info = {
        'gpu_info': gpu_info,
        'pytorch_version': torch.__version__,
        'cuda_test_passed': False
    }
    
    if gpu_info['cuda_available']:
        system_info['cuda_test_passed'] = test_cuda_functionality()
    
    return system_info

def print_system_summary():

    info = get_system_info()
    gpu = info['gpu_info']
    
    
    if gpu['cuda_available']:
        print(f"GPU: {gpu['gpu_name']}")
        print(f"Memoria GPU: {gpu['gpu_memory']:.1f}GB")
        
        if gpu['recommended_device'] == 'cuda':
            print("USANDO GPU")
        else:
            print("USANDO CPU")
    else:
        print("solo cpu")
    
    print("="*50 + "\n")

if __name__ == "__main__":
    print_system_summary()
