#ifndef _FAKE_DEFINES_H
#define _FAKE_DEFINES_H

#define	NULL	0
#define	BUFSIZ		1024
#define	FOPEN_MAX	20
#define	FILENAME_MAX	1024

#ifndef SEEK_SET
#define	SEEK_SET	0	/* set file offset to offset */
#endif
#ifndef SEEK_CUR
#define	SEEK_CUR	1	/* set file offset to current plus offset */
#endif
#ifndef SEEK_END
#define	SEEK_END	2	/* set file offset to EOF plus offset */
#endif


#define EXIT_FAILURE 1
#define EXIT_SUCCESS 0

#define RAND_MAX 32767
#define INT_MAX 32767

/* C99 stdbool.h defines */
#define __bool_true_false_are_defined 1
#define false 0
#define true 1

#endif
