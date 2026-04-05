import cProfile
from integrity import verify_chain

cProfile.run('verify_chain()', 'profile_output.prof')

import pstats
p = pstats.Stats('profile_output.prof')
p.sort_stats('cumulative').print_stats(20)