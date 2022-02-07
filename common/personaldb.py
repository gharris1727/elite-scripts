import collections
import json
import re


class Writer:
    def __init__(self, conn, debug):
        self.conn = conn
        self.debug = debug
        self.schema_cache = {}

    TYPE_MAPS = collections.defaultdict(lambda: lambda x: x)
    TYPE_MAPS[list] = TYPE_MAPS[dict] = TYPE_MAPS[tuple] = TYPE_MAPS[collections.OrderedDict] = json.dumps

    def set_schema(self, table, *schema):
        old_schema = self._get_schema(table)
        if not old_schema:
            self._change_table(table, "CREATE TABLE %s (%s)" % (table, ",".join(schema)))
        else:
            for col in set(schema) - set(old_schema):
                self._change_table(table, "ALTER TABLE %s ADD COLUMN %s" % (table, col))

    def _change_table(self, table, sql):
        self.execute(sql)
        if table in self.schema_cache:
            del self.schema_cache[table]

    def _get_schema(self, table):
        if table in self.schema_cache:
            return self.schema_cache[table]
        res = self.execute(
            "SELECT sql FROM sqlite_master WHERE tbl_name = ? AND type = 'table'",
            [table]
        ).fetchone()
        if not res:
            return None
        sql = res[0]
        typedef = [s.strip() for s in re.split(",", sql[sql.index('(')+1:sql.rindex(')')])]
        self.schema_cache[table] = typedef
        return typedef

    def insert(self, table, **kwargs):
        columns = kwargs.keys()
        return self.execute(
            "INSERT INTO %s (%s) VALUES (%s)" % (
                table,
                ",".join(["\"" + k + "\"" for k in columns]),
                ",".join(["?" for _ in columns])
            ),
            [self.TYPE_MAPS[type(kwargs[k])](kwargs[k]) for k in columns]
        )

    def execute(self, *args):
        if self.debug:
            print(args[0])
        return self.conn.execute(*args)

    def commit(self, *args):
        return self.conn.commit(*args)


class GroupImport:
    def __init__(self, key, writer, importer, length):
        self.key = key
        self.writer = writer
        self.importer = importer
        self.length = length
        self.index = 0
        self.writer.set_schema("imports", "key TEXT PRIMARY KEY", "count INTEGER DEFAULT 0")
        self.writer.execute("INSERT OR IGNORE INTO imports (path) VALUES (?)", [self.key])
        self.imported = self.writer.execute("SELECT count FROM imports WHERE key = ?", [self.key]).fetchone()[0]

    def events(self, events):
        if self.length > self.imported:
            for event in events():
                if self.index > self.imported:
                    self.importer.event(event)
                self.index += 1
            self.writer.execute("UPDATE imports SET count = ? WHERE key = ?", [self.index, self.key])
            self.writer.commit()
            return self.index - self.imported
        return 0


class StructuredImport:

    def __init__(self, writer):
        self.writer = writer

    DEFAULT_TYPES = {
        str: 'TEXT',
        int: 'INTEGER',
        bool: 'BOOLEAN',
        list: 'JSON',
        float: 'REAL',
        dict: 'JSON',
        tuple: 'JSON',
        collections.OrderedDict: 'JSON'
    }

    def event(self, event):
        event_type = event['event']
        del event['event']
        self.writer.set_schema(
            "events",
            "id INTEGER PRIMARY KEY AUTOINCREMENT",
            "timestamp TIMESTAMP",
            "key TEXT",
            "index_in_path INTEGER",
            "type TEXT",
            "event JSON",
        )
        event['event_id'] = self.writer.insert(
            "events",
            timestamp=event['timestamp'],
            type=event_type,
            event=event
        ).lastrowid
        del event['timestamp']
        custom_fn = getattr(self, event_type)
        type_info = custom_fn(None)
        type_overrides = constraints = None
        if type_info:
            type_overrides, constraints = type_info

        def lookup_type(key):
            if type_overrides and key in type_overrides:
                return type_overrides[key]
            return self.DEFAULT_TYPES[type(event[key])]
        schema = []
        if constraints:
            schema.extend(constraints)
        schema.extend(['"' + k + '"' + lookup_type(k) for k in event.keys()])
        self.writer.set_schema(event_type, *schema)
        value_overrides = custom_fn(event)
        if value_overrides:
            event = value_overrides
        self.writer.insert(event_type, **event)

    def ApproachSettlement(self, approachsettlement):
        pass
    def BackPack(self, backpack):
        pass
    def BackpackChange(self, backpackchange):
        pass
    def BookTaxi(self, booktaxi):
        pass
    def BuyAmmo(self, buyammo):
        pass
    def BuyDrones(self, buydrones):
        pass
    def BuyExplorationData(self, buyexplorationdata):
        pass
    def BuyTradeData(self, buytradedata):
        pass
    def CancelTaxi(self, canceltaxi):
        pass
    def Cargo(self, cargo):
        pass
    def CargoDepot(self, cargodepot):
        pass
    def CarrierJump(self, carrierjump):
        pass
    def CodexEntry(self, codexentry):
        pass
    def CollectCargo(self, collectcargo):
        pass
    def CommitCrime(self, commitcrime):
        pass
    def CommunityGoal(self, communitygoal):
        pass
    def CommunityGoalDiscard(self, communitygoaldiscard):
        pass
    def CommunityGoalJoin(self, communitygoaljoin):
        pass
    def CommunityGoalReward(self, communitygoalreward):
        pass
    def CrewHire(self, crewhire):
        pass
    def Died(self, died):
        pass
    def Docked(self, docked):
        pass
    def EjectCargo(self, ejectcargo):
        pass
    def EngineerContribution(self, engineercontribution):
        pass
    def EngineerCraft(self, engineercraft):
        pass
    def EngineerProgress(self, engineerprogress):
        pass
    def FSDJump(self, fsdjump):
        pass
    def FSDTarget(self, fsdtarget):
        pass
    def FSSAllBodiesFound(self, fssallbodiesfound):
        pass
    def FSSDiscoveryScan(self, fssdiscoveryscan):
        pass
    def FetchRemoteModule(self, fetchremotemodule):
        pass
    def Friends(self, friends):
        pass
    def Interdicted(self, interdicted):
        pass
    def Interdiction(self, interdiction):
        pass
    def JoinACrew(self, joinacrew):
        pass
    def LoadGame(self, loadgame):
        pass
    def Loadout(self, loadout):
        pass
    def Location(self, location):
        pass
    def MarketBuy(self, marketbuy):
        pass
    def MarketSell(self, marketsell):
        pass
    def MaterialCollected(self, materialcollected):
        pass
    def MaterialDiscarded(self, materialdiscarded):
        pass
    def MaterialTrade(self, materialtrade):
        pass
    def Materials(self, materials):
        pass
    def MiningRefined(self, miningrefined):
        pass
    def MissionAbandoned(self, missionabandoned):
        pass
    def MissionAccepted(self, missionaccepted):
        pass
    def MissionCompleted(self, missioncompleted):
        pass
    def MissionFailed(self, missionfailed):
        pass
    def MissionRedirected(self, missionredirected):
        pass
    def Missions(self, missions):
        pass
    def ModuleBuy(self, modulebuy):
        pass
    def ModuleRetrieve(self, moduleretrieve):
        pass
    def ModuleSell(self, modulesell):
        pass
    def ModuleSellRemote(self, modulesellremote):
        pass
    def MultiSellExplorationData(self, multisellexplorationdata):
        pass
    def NpcCrewPaidWage(self, npccrewpaidwage):
        pass
    def PayBounties(self, paybounties):
        pass
    def PayFines(self, payfines):
        pass
    def PayLegacyFines(self, paylegacyfines):
        pass
    def Powerplay(self, powerplay):
        pass
    def PowerplayCollect(self, powerplaycollect):
        pass
    def PowerplayDefect(self, powerplaydefect):
        pass
    def PowerplayDeliver(self, powerplaydeliver):
        pass
    def PowerplayFastTrack(self, powerplayfasttrack):
        pass
    def PowerplayJoin(self, powerplayjoin):
        pass
    def PowerplayLeave(self, powerplayleave):
        pass
    def PowerplaySalary(self, powerplaysalary):
        pass
    def Progress(self, progress):
        pass
    def Promotion(self, promotion):
        pass
    def QuitACrew(self, quitacrew):
        pass
    def Rank(self, rank):
        pass
    def RedeemVoucher(self, redeemvoucher):
        pass
    def RefuelAll(self, refuelall):
        pass
    def RefuelPartial(self, refuelpartial):
        pass
    def Repair(self, repair):
        pass
    def RepairAll(self, repairall):
        pass
    def Reputation(self, reputation):
        pass
    def RestockVehicle(self, restockvehicle):
        pass
    def Resurrect(self, resurrect):
        pass
    def SAASignalsFound(self, saascancomplete):
        pass
    def SAAScanComplete(self, saascancomplete):
        pass
    def Scan(self, scan):
        pass
    def ScientificResearch(self, scientificresearch):
        pass
    def SearchAndRescue(self, searchandrescue):
        pass
    def SelfDestruct(self, selfdestruct):
        pass
    def SellDrones(self, selldrones):
        pass
    def SellExplorationData(self, sellexplorationdata):
        pass
    def SellShipOnRebuy(self, sellshiponrebuy):
        pass
    def SetUserShipName(self, setusershipname):
        pass
    def ShipLocker(self, shiplocker):
        pass
    def ShipyardBuy(self, shipyardbuy):
        pass
    def ShipyardSell(self, shipyardsell):
        pass
    def ShipyardSwap(self, shipyardswap):
        pass
    def ShipyardTransfer(self, shipyardtransfer):
        pass
    def StartUp(self, startup):
        pass
    def Statistics(self, statistics):
        pass
    def StoredShips(self, storedships):
        pass
    def Synthesis(self, synthesis):
        pass
    def TechnologyBroker(self, technologybroker):
        pass
    def USSDrop(self, ussdrop):
        pass
    def Undocked(self, undocked):
        pass
    def AfmuRepairs(self, afmurepairs):
        pass
    def AppliedToSquadron(self, appliedtosquadron):
        pass
    def ApproachBody(self, approachbody):
        pass
    def AsteroidCracked(self, asteroidcracked):
        pass
    def BookDropship(self, bookdropship):
        pass
    def Bounty(self, bounty):
        pass
    def CancelDropship(self, canceldropship):
        pass
    def CapShipBond(self, capshipbond):
        pass
    def CargoTransfer(self, cargotransfer):
        pass
    def CarrierBankTransfer(self, carrierbanktransfer):
        pass
    def CarrierBuy(self, carrierbuy):
        pass
    def CarrierCrewServices(self, carriercrewservices):
        pass
    def CarrierDecommission(self, carrierdecommission):
        pass
    def CarrierDepositFuel(self, carrierdepositfuel):
        pass
    def CarrierDockingPermission(self, carrierdockingpermission):
        pass
    def CarrierFinance(self, carrierfinance):
        pass
    def CarrierJumpCancelled(self, carrierjumpcancelled):
        pass
    def CarrierJumpRequest(self, carrierjumprequest):
        pass
    def CarrierModulePack(self, carriermodulepack):
        pass
    def CarrierNameChange(self, carriernamechange):
        pass
    def CarrierStats(self, carrierstats):
        pass
    def CarrierTradeOrder(self, carriertradeorder):
        pass
    def ChangeCrewRole(self, changecrewrole):
        pass
    def ClearSavedGame(self, clearsavedgame):
        pass
    def CockpitBreached(self, cockpitbreached):
        pass
    def CollectItems(self, collectitems):
        pass
    def Commander(self, commander):
        pass
    def Continued(self, continued):
        pass
    def Coriolis(self, coriolis):
        pass
    def CrewAssign(self, crewassign):
        pass
    def CrewFire(self, crewfire):
        pass
    def CrewLaunchFighter(self, crewlaunchfighter):
        pass
    def CrewMemberJoins(self, crewmemberjoins):
        pass
    def CrewMemberQuits(self, crewmemberquits):
        pass
    def CrewMemberRoleChange(self, crewmemberrolechange):
        pass
    def CrimeVictim(self, crimevictim):
        pass
    def DataScanned(self, datascanned):
        pass
    def DatalinkScan(self, datalinkscan):
        pass
    def DatalinkVoucher(self, datalinkvoucher):
        pass
    def DisbandedSquadron(self, disbandedsquadron):
        pass
    def DiscoveryScan(self, discoveryscan):
        pass
    def DockFighter(self, dockfighter):
        pass
    def DockSRV(self, docksrv):
        pass
    def DockingCancelled(self, dockingcancelled):
        pass
    def DockingDenied(self, dockingdenied):
        pass
    def DockingGranted(self, dockinggranted):
        pass
    def DockingRequested(self, dockingrequested):
        pass
    def DockingTimeout(self, dockingtimeout):
        pass
    def DropItems(self, dropitems):
        pass
    def EDDCommodityPrices(self, eddcommodityprices):
        pass
    def EDDItemSet(self, edditemset):
        pass
    def EDShipyard(self, edshipyard):
        pass
    def Embark(self, embark):
        pass
    def EndCrewSession(self, endcrewsession):
        pass
    def EngineerApply(self, engineerapply):
        pass
    def EngineerLegacyConvert(self, engineerlegacyconvert):
        pass
    def EscapeInterdiction(self, escapeinterdiction):
        pass
    def FSSSignalDiscovered(self, fsssignaldiscovered):
        pass
    def FactionKillBond(self, factionkillbond):
        pass
    def FighterDestroyed(self, fighterdestroyed):
        pass
    def FighterRebuilt(self, fighterrebuilt):
        pass
    def Fileheader(self, fileheader):
        pass
    def FuelScoop(self, fuelscoop):
        pass
    def HeatDamage(self, heatdamage):
        pass
    def HeatWarning(self, heatwarning):
        pass
    def HullDamage(self, hulldamage):
        pass
    def InvitedToSquadron(self, invitedtosquadron):
        pass
    def JetConeBoost(self, jetconeboost):
        pass
    def JetConeDamage(self, jetconedamage):
        pass
    def JoinedSquadron(self, joinedsquadron):
        pass
    def KickCrewMember(self, kickcrewmember):
        pass
    def LaunchDrone(self, launchdrone):
        pass
    def LaunchFighter(self, launchfighter):
        pass
    def LaunchSRV(self, launchsrv):
        pass
    def LeaveBody(self, leavebody):
        pass
    def LeftSquadron(self, leftsquadron):
        pass
    def Liftoff(self, liftoff):
        pass
    def Market(self, market):
        pass
    def MassModuleStore(self, massmodulestore):
        pass
    def MaterialDiscovered(self, materialdiscovered):
        pass
    def ModuleArrived(self, modulearrived):
        pass
    def ModuleInfo(self, moduleinfo):
        pass
    def ModuleStore(self, modulestore):
        pass
    def ModuleSwap(self, moduleswap):
        pass
    def Music(self, music):
        pass
    def NavBeaconScan(self, navbeaconscan):
        pass
    def NavRoute(self, navroute):
        pass
    def NewCommander(self, newcommander):
        pass
    def NpcCrewRank(self, npccrewrank):
        pass
    def Outfitting(self, outfitting):
        pass
    def PVPKill(self, pvpkill):
        pass
    def Passengers(self, passengers):
        pass
    def PowerplayVote(self, powerplayvote):
        pass
    def PowerplayVoucher(self, powerplayvoucher):
        pass
    def ProspectedAsteroid(self, prospectedasteroid):
        pass
    def RebootRepair(self, rebootrepair):
        pass
    def ReceiveText(self, receivetext):
        pass
    def RepairDrone(self, repairdrone):
        pass
    def ReservoirReplenished(self, reservoirreplenished):
        pass
    def SRVDestroyed(self, srvdestroyed):
        pass
    def Scanned(self, scanned):
        pass
    def Screenshot(self, screenshot):
        pass
    def SendText(self, sendtext):
        pass
    def SharedBookmarkToSquadron(self, sharedbookmarktosquadron):
        pass
    def ShieldState(self, shieldstate):
        pass
    def ShipArrived(self, shiparrived):
        pass
    def ShipTargeted(self, shiptargeted):
        pass
    def Shipyard(self, shipyard):
        pass
    def ShipyardNew(self, shipyardnew):
        pass
    def ShutDown(self, shutdown):
        pass
    def Shutdown(self, shutdown):
        pass
    def SquadronCreated(self, squadroncreated):
        pass
    def SquadronStartup(self, squadronstartup):
        pass
    def StartJump(self, startjump):
        pass
    def Status(self, status):
        pass
    def StoredModules(self, storedmodules):
        pass
    def SupercruiseEntry(self, supercruiseentry):
        pass
    def SupercruiseExit(self, supercruiseexit):
        pass
    def SystemsShutdown(self, systemsshutdown):
        pass
    def Touchdown(self, touchdown):
        pass
    def UnderAttack(self, underattack):
        pass
    def VehicleSwitch(self, vehicleswitch):
        pass
    def WingAdd(self, wingadd):
        pass
    def WingInvite(self, winginvite):
        pass
    def WingJoin(self, wingjoin):
        pass
    def WingLeave(self, wingleave):
        pass
    def DetailedTrafficReport(self, detailedtrafficreport):
        pass
    def LocalFactionStatusSummary(self, localfactionstatussummary):
        pass
    def LocalFactionBounties(self, localfactionbounties):
        pass
    def LocalPowerBounties(self, localpowerbounties):
        pass
    def LocalPowerUpdate(self, localpowerupdate):
        pass
    def LocalTradeReport(self, localtradereport):
        pass
    def LocalCrimeReport(self, localcrimereport):
        pass
    def LocalBountyReport(self, localbountyreport):
        pass
