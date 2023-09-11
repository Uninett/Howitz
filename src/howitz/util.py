import datetime

from curitz import cli


def create_case(case):
    common = {}

    try:
        age = datetime.datetime.now() - case.opened
        common["id"] = case.id
        common["router"] = case.router
        common["admstate"] = case.state.value[:7]
        common["age"] = cli.strfdelta(age, "{days:2d}d {hours:02}:{minutes:02}")
        common["priority"] = case.priority
        if "downtime" in case.keys():
            common["downtime"] = cli.downtimeShortner(case.downtime)
        else:
            common["downtime"] = ""

        if case.type == cli.caseType.PORTSTATE:
            common["opstate"] = "PORT %s" % case.portstate[0:5]
            common["port"] = cli.interfaceRenamer(case.port)
            common["description"] = case.get("descr", "")
        elif case.type == cli.caseType.BGP:
            common["opstate"] = "BGP  %s" % case.bgpos[0:5]
            common["port"] = "AS{}".format(case.remote_as)
            common["description"] = "%s %s" % (
                cli.dns_reverse_resolver(str(case.remote_addr)),
                case.get("lastevent", ""),
            )
        elif case.type == cli.caseType.BFD:
            try:
                port = case.bfdaddr
            except Exception:
                port = "ix {}".format(case.bfdix)

            common["opstate"] = "BFD  %s" % case.bfdstate[0:5]
            common["port"] = str(port)
            common["description"] = "{}, {}".format(
                case.get("neigh_rdns"), case.get("lastevent")
            )
        elif case.type == cli.caseType.REACHABILITY:
            common["opstate"] = case.reachability
            common["port"] = ""
            common["description"] = ""
        elif case.type == cli.caseType.ALARM:
            common["opstate"] = "ALRM {}".format(case.alarm_type)
            common["port"] = ""
            common["description"] = case.lastevent
    except Exception:
        raise

    return common

