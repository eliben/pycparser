#include "some.h"

#ifdef FOO
	void main(unsigned char c){
		printf("foo", c);
		printf("bar");
	}
#endif
