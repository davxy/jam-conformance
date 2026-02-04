import os
import logging

# Global registry for spec-dependent classes
_spec_dependent_classes = []

def spec_metaclass(base_metaclass):
    """Create a metaclass that combines spec dependency with the base metaclass."""
    class SpecDependentMeta(base_metaclass):
        def __new__(mcs, name, bases, namespace, **kwargs):
            cls = super().__new__(mcs, name, bases, namespace, **kwargs)
            
            # Check if this class has spec-dependent attributes
            spec_attrs = getattr(cls, '_spec_attributes', {})
            if spec_attrs:
                _spec_dependent_classes.append((cls, spec_attrs))
            
            return cls
    
    return SpecDependentMeta

# Spec configurations
SPECS = {
    'full': {
        'validators_count': 1023,
        'epoch_length': 600,
        'max_tickets_per_block': 16,
    },
    'tiny': {
        'validators_count': 6,
        'epoch_length': 12,
        'max_tickets_per_block': 3,
    }
}

# Get spec from environment variable, default to 'tiny'
_current_spec = os.environ.get('JAM_SPEC', 'full').lower()

def set_spec(spec_name):
    """Set the current spec configuration."""
    global _current_spec
    if spec_name not in SPECS:
        raise ValueError(f"Unknown spec: {spec_name}. Available specs: {list(SPECS.keys())}")
    _current_spec = spec_name
    _update_globals()
    _update_type_classes()

def get_current_spec():
    """Get the name of the current spec."""
    return _current_spec

def _update_globals():
    """Update all derived globals based on current spec."""
    global validators_count, epoch_length, max_tickets_per_block
    global validators_per_core, core_count, validators_super_majority, avail_bitfield_bytes
    global auth_pool_max_size, auth_queue_size, hash_size
    global recent_blocks_max_size
    
    logging.debug("Using JAM spec: %s", _current_spec)
    spec = SPECS[_current_spec]
    
    # Base globals from spec
    validators_count = spec['validators_count']
    epoch_length = spec['epoch_length']
    max_tickets_per_block = spec['max_tickets_per_block']
    
    # Derived values
    validators_per_core = 3
    core_count = validators_count // validators_per_core
    validators_super_majority = validators_count // 3 * 2 + 1
    avail_bitfield_bytes = (core_count + 7) // 8
    
    # Fixed values
    auth_pool_max_size = 8
    auth_queue_size = 80
    hash_size = 32
    recent_blocks_max_size = 8

def _update_type_classes():
    """Update all registered spec-dependent classes."""
    for cls, spec_attrs in _spec_dependent_classes:
        for attr_name, glob_name in spec_attrs.items():
            logging.debug("Updating {} {} = {}".format(cls, attr_name, globals()[glob_name]))
            setattr(cls, attr_name, globals()[glob_name])

# Initialize globals with current spec
_update_globals()
