#ifndef _FAKE_FUNCTION_DECLARATIONS_H
#define _FAKE_FUNCTION_DECLARATIONS_H

#include "_fake_defines.h"
#include "_fake_typedefs.h"

Status XGetClassHint(
    Display*      /* display */,
    Window     /* w */,
    XClassHint*      /* class_hints_return */
);

Screen *XtScreen(
    Widget     /* widget */
);

XSelectionRequestEvent *XtGetSelectionRequest(
    Widget 		/* widget */,
    Atom 		/* selection */,
    XtRequestId 	/* request_id */
);

#endif
