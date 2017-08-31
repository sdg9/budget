ImportToYNAB()

Func ImportToYNAB()

    Local $importFile = $CmdLine[1]
    Local $exeLocation = "C:\Program Files (x86)\YNAB 4\YNAB 4.exe"
    Local $class = "ApolloRuntimeContentWindow"

    If WinExists("[CLASS:" & $class & "]","") Then
        WinActivate("[CLASS:" & $class & "]","")
    Else
        Local $iPID = Run($exeLocation)
        WinWait("[CLASS:ApolloRuntimeContentWindow]", "", 10)
        Sleep(10000)
    EndIf
    Sleep(500)
    Send("^i")
    ClipPut($importFile)
    sleep(500)
    Send("^v")


    ; Close the Notepad process using the PID returned by Run.
    ;ProcessClose($iPID)
EndFunc   ;==>ImportToYNAB
    
