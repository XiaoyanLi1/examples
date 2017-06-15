import argparse
import os
import shutil
import time

import numpy as np
import pandas as pd

import torch
import torch.nn as nn
import torch.nn.parallel
import torch.backends.cudnn as cudnn
import torch.optim
import torch.utils.data
import torchvision.transforms as transforms
import torchvision.datasets as datasets
import torchvision.models as models

import resnext
import meta_model.FractAllNeXt



model_names = sorted(name for name in models.__dict__
    if name.islower() and not name.startswith("__")
    and callable(models.__dict__[name]))


resnext_models = {'resnext50':resnext.resnext50,
                  'resnext29_cifar10':resnext.resnext29_cifar10,
                  'resnext29_cifar100':resnext.resnext29_cifar100,
                  'resnext29_cifar100_bone':resnext.resnext29_cifar100_bone,
                  'resnext38_imagenet1k':resnext.resnext38_imagenet1k,
                  'resnext38_inaturalist':resnext.resnext38_inaturalist,
                  'resnext50_imagenet1k':resnext.resnext50_imagenet1k,
                  'resnext50_inaturalist':resnext.resnext50_inaturalist,
                  'resnext50my':resnext.resnext50my,
                  'resnext50L1':resnext.resnext50L1,
                  'resnext50myL1':resnext.resnext50myL1,
                  'resnext38':resnext.resnext38,
                  'resnext26':resnext.resnext26,
                  'resnext50x2':resnext.resnext50x2,
                  'resnext50v':resnext.resnext50v,
                  'resnext50hgs':resnext.resnext50hgs,
                  'resnext101':resnext.resnext101,
                  'resnext101v':resnext.resnext101v,
                  'resnext152':resnext.resnext152,
                  'resnet50':resnext.resnet50,
                  'faresnext50':meta_model.FractAllNeXt.faresnext50,
                  'faresnext50v2':meta_model.FractAllNeXt.faresnext50v2,
                  'faresnext50v3':meta_model.FractAllNeXt.faresnext50v3,
                  'faresnext101v2':meta_model.FractAllNeXt.faresnext101v2,
                  'faresnext101v3':meta_model.FractAllNeXt.faresnext101v3}

parser = argparse.ArgumentParser(description='PyTorch ImageNet Training')
parser.add_argument('data', metavar='DIR',
                    help='path to dataset')

parser.add_argument('--arch', '-a', metavar='ARCH', default='faresnext50',
                    choices=resnext_models.keys(),
                    help='model architecture: ' +
                        ' | '.join(resnext_models.keys()) +
                        ' (default: faresnext50)')

parser.add_argument('-j', '--workers', default=4, type=int, metavar='N',
                    help='number of data loading workers (default: 4)')
parser.add_argument('--tl', '--train-loops', default=1, type=int, metavar='N',
                    help='number of data training loops during 1 epoch (default: 1)')

parser.add_argument('--ds', '--data-set', default='dir', type=str, metavar='S',
                    help='default dataset')

parser.add_argument('--epochs', default=300, type=int, metavar='N',
                    help='number of total epochs to run')
parser.add_argument('--start-epoch', default=0, type=int, metavar='N',
                    help='manual epoch number (useful on restarts)')
parser.add_argument('-b', '--batch-size', default=256, type=int,
                    metavar='N', help='mini-batch size (default: 256)')

parser.add_argument('--xp', '--expansion-coef', default=2, type=float,
                    metavar='N', help='expansion-coef')

parser.add_argument('--x', '--num-channels', default=32, type=int,
                    metavar='N', help='num of channels')

parser.add_argument('--nes', '--nesterov', default=1, type=int,
                    metavar='N', help='nesterov momentum')

parser.add_argument('--secord', '--second-order', default=0, type=int,
                    metavar='N', help='second-order')

parser.add_argument('--soadd', '--second-order-add', default=0.01, type=float,
                    metavar='N', help='second-order-add')

parser.add_argument('--att', '--attention-model', default=0, type=int,
                    metavar='N', help='attention')

parser.add_argument('--lastout' , default= 7 , type=int,
                    metavar='N', help='lastout')

parser.add_argument('--d', '--channel-width', default=4, type=int,
                    metavar='N', help='channel width')

parser.add_argument('--ug', '--up-group', default=0, type=int,
                    metavar='N', help='up-group')

parser.add_argument('--dg', '--down-group', default=0, type=int,
                    metavar='N', help='down-group')

parser.add_argument('--L1', '--L1-mode', default=0, type=int,
                    metavar='N', help='L1-mode, loss form')

parser.add_argument('--nclass', '--num-classes', default=1000, type=int,
                    metavar='N', help='mini-batch size (default: 256)')

parser.add_argument('--lr', '--learning-rate', default=0.1, type=float,
                    metavar='LR', help='initial learning rate')
parser.add_argument('--lp','--learning-policy',default=20, type=int,
                   metavar='LP', help='learning policy: every lp epochs lr*=0.1')
parser.add_argument('--momentum', default=0.9, type=float, metavar='M',
                    help='momentum')
parser.add_argument('--weight-decay', '--wd', default=1e-4, type=float,
                    metavar='W', help='weight decay (default: 1e-4)')

parser.add_argument('--my', '--multi-way', default=0, type=int,
                    metavar='MultiWay Softmax', help='MultiWay Softmax is kind of Ensemble')

parser.add_argument('--print-freq', '-p', default=20, type=int,
                    metavar='N', help='print frequency (default: 20)')

parser.add_argument('--resume', default='', type=str, metavar='PATH',
                    help='path to latest checkpoint (default: none)')

parser.add_argument('--dp', default='', type=str, metavar='Dilation Pattern (Vertical )',
                   help='Dilation Pattern: LIN,EXP,REVLIN,REVEXP,HOURGLASS,SHUTTLE')

parser.add_argument('--df', default=0, type=int, metavar='Deformable Flag',
                   help='Deformable Flag: Whether Deformable? May Cause Parameter Inflation')

parser.add_argument('-e', '--evaluate', default=0, type=int, metavar='N',
                    help='evaluate model on validation set')

parser.add_argument('--evalmodnum', default=1, type=int, metavar='N',
                    help='evaluate expansion')

parser.add_argument('--evaltardir', default='./', type=str, metavar='N',
                    help='evaluate dir')

parser.add_argument('--pretrained', dest='pretrained', action='store_true',
                    help='use pre-trained model')

best_prec1 = 0


def main():
    global args, best_prec1
    args = parser.parse_args()

    # create model
    
    if 'cifar' in args.arch:
        print "CIFAR Model Fix args.lastout As 8"
        args.lastout += 1
        
    
    if args.pretrained:
        print("=> using pre-trained model '{}'".format(args.arch))
        model = resnext_models[args.arch](pretrained=True, expansion = args.xp, x = args.x, d = args.d, \
                                         upgroup = True if args.ug else False, downgroup = True if args.dg else False,\
                                         secord = True if args.secord else False, soadd = args.soadd, \
                                         att = True if args.att else False, lastout = args.lastout, dilpat = args.dp, \
                                         deform = True if args.df else False)
    else:
        print("=> creating model '{}'".format(args.arch))
        model = resnext_models[args.arch](expansion = args.xp, x = args.x , d = args.d, \
                                         upgroup = True if args.ug else False, downgroup = True if args.dg else False,\
                                         secord = True if args.secord else False, soadd = args.soadd, \
                                         att = True if args.att else False, lastout = args.lastout, dilpat = args.dp)
    
    
    # get the number of model parameters
    print('Number of model parameters: {}'.format(
        sum([p.data.nelement() for p in model.parameters()])))
    
    if args.arch.startswith('alexnet') or args.arch.startswith('vgg'):
        model.features = torch.nn.DataParallel(model.features)
        model.cuda()
    else:
        model = torch.nn.DataParallel(model).cuda()

    # optionally resume from a checkpoint
    if args.resume:
        if os.path.isfile(args.resume):
            print("=> loading checkpoint '{}'".format(args.resume))
            checkpoint = torch.load(args.resume)
            args.start_epoch = checkpoint['epoch']
            best_prec1 = checkpoint['best_prec1']
            model.load_state_dict(checkpoint['state_dict'])
            print("=> loaded checkpoint '{}' (epoch {})"
                  .format(args.resume, checkpoint['epoch']))
        else:
            print("=> no checkpoint found at '{}'".format(args.resume))

    cudnn.benchmark = True

    # Data loading code
    if args.ds == "dir":
        traindir = os.path.join(args.data, 'train')
        valdir = os.path.join(args.data, 'val')
        normalize = transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                     std=[0.229, 0.224, 0.225])

        train_loader = torch.utils.data.DataLoader(
            datasets.ImageFolder(traindir, transforms.Compose([
                transforms.RandomSizedCrop(args.lastout*32),
                transforms.RandomHorizontalFlip(),
                transforms.ToTensor(),
                normalize,
            ])),
            batch_size=args.batch_size, shuffle=True,
            num_workers=args.workers, pin_memory=True)
        
        if args.evaluate == 2:
            
            val_loader = torch.utils.data.DataLoader(
                datasets.ImageFolder(valdir, transforms.Compose([
                    transforms.Scale((args.lastout+args.evalmodnum)*32),
                    transforms.CenterCrop(args.lastout*32),
                    transforms.RandomHorizontalFlip(),
                    transforms.ToTensor(),
                    normalize,
                ])),
                batch_size=args.batch_size, shuffle=False,
            num_workers=args.workers, pin_memory=True)
        
        if args.evaluate == 3:
            
            val_loader = torch.utils.data.DataLoader(
                datasets.ImageFolder(valdir, transforms.Compose([
                    transforms.Scale((args.lastout+args.evalmodnum)*32),
                    transforms.RandomCrop((args.lastout+args.evalmodnum)*32),
                    transforms.RandomCrop(args.lastout*32),
                    transforms.RandomHorizontalFlip(),
                    transforms.ToTensor(),
                    normalize,
                ])),
                batch_size=args.batch_size, shuffle=False,
            num_workers=args.workers, pin_memory=True)
            
        else:
            
            val_loader = torch.utils.data.DataLoader(
                datasets.ImageFolder(valdir, transforms.Compose([
                    transforms.Scale((args.lastout+1)*32),
                    transforms.CenterCrop(args.lastout*32),
                    transforms.ToTensor(),
                    normalize,
                ])),
                batch_size=args.batch_size, shuffle=False,
                num_workers=args.workers, pin_memory=True)
        
    elif args.ds in ["CIFAR10","CIFAR100"]:
        normalize = transforms.Normalize(mean=[x/255.0 for x in [125.3, 123.0, 113.9]],
                                     std=[x/255.0 for x in [63.0, 62.1, 66.7]])
        transform_train = transforms.Compose([
            transforms.RandomCrop(32, padding=4),
            transforms.RandomHorizontalFlip(),
            transforms.ToTensor(),
            normalize,
            ])
        
        transform_test = transforms.Compose([
            transforms.ToTensor(),
            normalize
            ])
        
        if args.ds == "CIFAR10":
            
            train_loader = torch.utils.data.DataLoader(
                datasets.CIFAR10('../data', train=True, download=True,
                             transform=transform_train),
                             batch_size=args.batch_size, shuffle=True, num_workers=args.workers, pin_memory=True)
            val_loader = torch.utils.data.DataLoader(
                datasets.CIFAR10('../data', train=False, transform=transform_test),
                batch_size=args.batch_size, shuffle=False, num_workers=args.workers, pin_memory=True)
        else:
            
            train_loader = torch.utils.data.DataLoader(
                datasets.CIFAR100('../data', train=True, download=True,
                             transform=transform_train),
                             batch_size=args.batch_size, shuffle=True, num_workers=args.workers, pin_memory=True)
            val_loader = torch.utils.data.DataLoader(
                datasets.CIFAR100('../data', train=False, transform=transform_test),
                batch_size=args.batch_size, shuffle=False, num_workers=args.workers, pin_memory=True)
        
    else:
        print "Unrecognized Dataset. Halt."
        return 0
        
        
    # define loss function (criterion) and pptimizer
    #criterion = nn.CrossEntropyLoss().cuda()
    if 'L1' in args.arch or args.L1 == 1:
        criterion = nn.L1Loss(size_average=True).cuda()
    elif 'my' in args.arch:
        criterion = nn.NLLLoss().cuda()
    else:
        criterion = nn.CrossEntropyLoss().cuda()

    optimizer = torch.optim.SGD(model.parameters(), args.lr,
                                momentum=args.momentum,
                                weight_decay=args.weight_decay,nesterov=False if args.nes == 0 else True)

    if args.evaluate == 2 :
        NUM_MULTICROP = 1
        for i in range(0,NUM_MULTICROP):
            test_output(val_loader, model, 'Result_{0}_{1}_{2}'.format(args.evaluate, i, args.evalmodnum))
        return
    
    elif args.evaluate == 3 :
        NUM_MULTICROP = 36
        for i in range(10,NUM_MULTICROP):
            # Reset Val_Loader!!
            val_loader = torch.utils.data.DataLoader(
                datasets.ImageFolder(valdir, transforms.Compose([
                    transforms.Scale((args.lastout+args.evalmodnum)*32),
                    transforms.RandomCrop((args.lastout+args.evalmodnum)*32),
                    transforms.RandomCrop(args.lastout*32),
                    transforms.RandomHorizontalFlip(),
                    transforms.ToTensor(),
                    normalize,
                ])),
                batch_size=args.batch_size, shuffle=False,
            num_workers=args.workers, pin_memory=True)
            # Test
            test_output(val_loader, model, args.evaltardir+'Result_{0}_{1}_{2}'.format(args.evaluate, i, args.evalmodnum))
        return
    
    elif args.evaluate == 1:
        test_output(val_loader, model, 'Result_00')
        return

    for epoch in range(args.start_epoch, args.epochs):
        adjust_learning_rate(optimizer, epoch)

        # train for one epoch
        for i in range(args.tl):
            train(train_loader, model, criterion, optimizer, epoch)

        # evaluate on validation set
        prec1 = validate(val_loader, model, criterion)

        # remember best prec@1 and save checkpoint
        is_best = prec1 > best_prec1
        best_prec1 = max(prec1, best_prec1)
        save_checkpoint({
            'epoch': epoch + 1,
            'arch': args.arch,
            'state_dict': model.state_dict(),
            'best_prec1': best_prec1,
        }, is_best)
        print 'Current best accuracy: ', best_prec1
    print 'Global best accuracy: ', best_prec1


def train(train_loader, model, criterion, optimizer, epoch):
    batch_time = AverageMeter()
    data_time = AverageMeter()
    losses = AverageMeter()
    top1 = AverageMeter()
    top5 = AverageMeter()

    # switch to train mode
    model.train()

    end = time.time()
    for i, (input, target) in enumerate(train_loader):
        # measure data loading time
        data_time.update(time.time() - end)
        #print type(target.float())
        if 'L1' in args.arch or args.L1==1:
            targetTensor = np.zeros((args.batch_size, args.nclass))
            for j in range(args.batch_size):
                targetTensor[j, target[j]] = 1.0
            #targetTensor = targetTensor[:input.size[0],:input.size[1]]
            targetTensor = torch.FloatTensor(targetTensor)
            targetTensor = targetTensor.cuda(async=True)
            target = target.cuda(async=True)
            target_var = torch.autograd.Variable(targetTensor)
        else:    
            target = target.cuda(async=True)
            target_var = torch.autograd.Variable(target)
            
        input_var = torch.autograd.Variable(input)
        

        # compute output
        output = model(input_var)
        loss = criterion(output, target_var)

        # measure accuracy and record loss
        prec1, prec5 = accuracy(output.data, target, topk=(1, 5))
        losses.update(loss.data[0], input.size(0))
        top1.update(prec1[0], input.size(0))
        top5.update(prec5[0], input.size(0))

        # compute gradient and do SGD step
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        # measure elapsed time
        batch_time.update(time.time() - end)
        end = time.time()

        if i % args.print_freq == 0:
            print('Epoch: [{0}][{1}/{2}]\t'
                  'Time {batch_time.val:.3f} ({batch_time.avg:.3f})\t'
                  'Data {data_time.val:.3f} ({data_time.avg:.3f})\t'
                  'Loss {loss.val:.4f} ({loss.avg:.4f})\t'
                  'Prec@1 {top1.val:.3f} ({top1.avg:.3f})\t'
                  'Prec@5 {top5.val:.3f} ({top5.avg:.3f})'.format(
                   epoch, i, len(train_loader), batch_time=batch_time,
                   data_time=data_time, loss=losses, top1=top1, top5=top5))


def validate(val_loader, model, criterion):
    batch_time = AverageMeter()
    losses = AverageMeter()
    top1 = AverageMeter()
    top5 = AverageMeter()

    # switch to evaluate mode
    model.eval()

    end = time.time()
    for i, (input, target) in enumerate(val_loader):
        
        if 'L1' in args.arch or args.L1 == 1:
            tmp = np.zeros((args.batch_size, args.nclass))
            for i in range(args.batch_size):
                tmp[i, target[i]] = 1.0
                
            # tmp and input ???
            target = torch.FloatTensor(tmp)
            target = target.cuda(async=True)
        else:    
            target = target.cuda(async=True)
            
        input_var = torch.autograd.Variable(input, volatile=True)
        target_var = torch.autograd.Variable(target, volatile=True)

        # compute output
        output = model(input_var)
        loss = criterion(output, target_var)

        # measure accuracy and record loss
        prec1, prec5 = accuracy(output.data, target, topk=(1, 5))
        losses.update(loss.data[0], input.size(0))
        top1.update(prec1[0], input.size(0))
        top5.update(prec5[0], input.size(0))

        # measure elapsed time
        batch_time.update(time.time() - end)
        end = time.time()

        if i % args.print_freq == 0:
            print('Test: [{0}/{1}]\t'
                  'Time {batch_time.val:.3f} ({batch_time.avg:.3f})\t'
                  'Loss {loss.val:.4f} ({loss.avg:.4f})\t'
                  'Prec@1 {top1.val:.3f} ({top1.avg:.3f})\t'
                  'Prec@5 {top5.val:.3f} ({top5.avg:.3f})'.format(
                   i, len(val_loader), batch_time=batch_time, loss=losses,
                   top1=top1, top5=top5))

    print(' * Prec@1 {top1.avg:.3f} Prec@5 {top5.avg:.3f}'
          .format(top1=top1, top5=top5))

    return top1.avg


def test_output(val_loader, model, output_name):
    batch_time = AverageMeter()

    # switch to evaluate mode
    model.eval()

    end = time.time()
    
    finalres = []
    for i, (input, target) in enumerate(val_loader):
        #if i>5:
        #    break
        if 'L1' in args.arch or args.L1 == 1:
            tmp = np.zeros((args.batch_size, args.nclass))
            for i in range(args.batch_size):
                tmp[i, target[i]] = 1.0
                
            # tmp and input ???
            target = torch.FloatTensor(tmp)
            target = target.cuda(async=True)
        else:    
            target = target.cuda(async=True)
            
        input_var = torch.autograd.Variable(input, volatile=True)
        target_var = torch.autograd.Variable(target, volatile=True)

        # compute output
        output = model(input_var)
        output = output.data.cpu().numpy()
        print i, output.shape
        finalres.append(pd.DataFrame(output))
    
    pd.concat(finalres,axis=0).to_hdf(output_name+'.hdf','result')
    print 'Finished Writing to HDF5 File.'


def save_checkpoint(state, is_best, filename='checkpoint.pth.tar'):
    torch.save(state, filename)
    if is_best:
        shutil.copyfile(filename, 'model_best.pth.tar')


class AverageMeter(object):
    """Computes and stores the average and current value"""
    def __init__(self):
        self.reset()

    def reset(self):
        self.val = 0
        self.avg = 0
        self.sum = 0
        self.count = 0

    def update(self, val, n=1):
        self.val = val
        self.sum += val * n
        self.count += n
        self.avg = self.sum / self.count


def adjust_learning_rate(optimizer, epoch):
    """Sets the learning rate to the initial LR decayed by 10 every 30/30/30/30 epochs"""
    """The following pattern is just an example. Please modify yourself."""
    if args.lp > 0:
        lr = args.lr * (0.1 ** (epoch >= args.lp)) * (0.1 ** (epoch >= (args.lp*1.6 ))) * (0.1 ** (epoch >= (args.lp*1.9))) * \
                    (0.1 ** (epoch >= (args.lp*2.2))) * (0.1 ** (epoch >= (args.lp*5)))
    else:
        lr = args.lr if ( epoch < 400 ) else args.lr*0.1
        if 'L1' in args.arch or args.L1 == 1:
            lr = lr
            #lr = lr * args.batch_size
    for param_group in optimizer.param_groups:
        param_group['lr'] = lr


def accuracy(output, target, topk=(1,)):
    """Computes the precision@k for the specified values of k"""
    maxk = max(topk)
    batch_size = target.size(0)

    _, pred = output.topk(maxk, 1, True, True)
    pred = pred.t()
    correct = pred.eq(target.view(1, -1).expand_as(pred))

    res = []
    for k in topk:
        correct_k = correct[:k].view(-1).float().sum(0)
        res.append(correct_k.mul_(100.0 / batch_size))
    return res


if __name__ == '__main__':
    main()
